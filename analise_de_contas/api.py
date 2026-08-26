"""
🏢 Análise de Contas Condominiais v7.0 — FastAPI REST Backend
Expõe toda a funcionalidade do pipeline como API para o frontend React.
"""

import os
import re
import json
import time
import uuid
import subprocess
import threading
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from utils import (
    sanitize_filename,
    find_all_peer_review_dirs,
    format_file_size,
    extract_nota_from_synthesis,
)
from security import validate_pdf_upload, get_auth_password, MAX_UPLOAD_MB, COMPRESS_THRESHOLD_MB

# ===== Dotenv =====
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# ===== Config =====
APP_DIR = Path(__file__).resolve().parent
BASE_DIR = Path(os.environ.get("ANALISE_BASE_DIR", APP_DIR.parent))
PIPELINE_SCRIPT = APP_DIR / "pipeline" / "runner.py"
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_BASE_DIR = BASE_DIR / "Arquivos das bancas"


def _allowed_origins() -> list[str]:
    """Origens permitidas pelo CORS. Lê ALLOWED_ORIGINS (csv) do env.

    Default seguro para dev local: Vite (:5173) + API (:8000).
    Em produção, defina ALLOWED_ORIGINS="https://app.exemplo.com".
    """
    raw = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8000")
    return [o.strip() for o in raw.split(",") if o.strip()]

# ===== FastAPI App =====
app = FastAPI(
    title="Análise de Contas Condominiais API",
    description="Backend REST para o pipeline de auditoria de contas condominiais via NotebookLM",
    version="7.0.0",
)

app.add_middleware(
    CORSMiddleware,
    # Lista explícita de origens (env), sem wildcard — evita o problema de
    # allow_credentials=True + allow_origins=["*"].
    allow_origins=_allowed_origins(),
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
    max_age=600,
)

# ===== Autenticação via API Key =====
_API_KEY = get_auth_password()  # Reusa ANALISE_PASSWORD do env


@app.middleware("http")
async def require_api_key(request: Request, call_next):
    """Exige X-API-Key nas rotas /api/, exceto health e config."""
    path = request.url.path

    # Rotas públicas (não exigem autenticação)
    exempt_paths = {"/api/health", "/api/config", "/docs", "/redoc", "/openapi.json"}
    if path in exempt_paths or path.startswith(("/docs/", "/redoc/", "/openapi.json")):
        return await call_next(request)

    # Se não há chave configurada, auth é opcional (dev mode)
    if not _API_KEY:
        return await call_next(request)

    # Verificar header X-API-Key
    api_key = request.headers.get("X-API-Key", "")
    # Comparação direta (API Key em texto plano do env, não hash)
    from security import secrets
    if not secrets.compare_digest(api_key, _API_KEY):
        return JSONResponse(
            status_code=401,
            content={"detail": "API Key inválida. Forneça o header X-API-Key."},
        )

    return await call_next(request)


# ===== Pipeline State (in-memory + filesystem) =====
# Track running pipeline processes. A fonte de verdade do "está rodando?" é
# este registry (qualquer entry com status "running"). O lock de escrita por
# diretório fica no pipeline/lock.py (fcntl) — manter dois locks JSON globais
# só gera race conditions.
_pipeline_registry: dict[str, dict] = {}


def _any_pipeline_running() -> bool:
    """Verdade: existe pipeline com status running neste processo uvicorn?"""
    return any(e.get("status") == "running" for e in _pipeline_registry.values())


# ===== Models =====
class PipelineConfig(BaseModel):
    domain: str = "res"
    mode: str = "full"
    force: bool = False
    output_dir: Optional[str] = None


class AnalysisInfo(BaseModel):
    id: str
    name: str
    path: str
    file_count: int
    size: str
    modified: str
    modules_completed: list[str]
    has_csv: bool
    has_presentations: list[str]
    has_artifacts: bool


# ===== Helper Functions =====

def _get_analyses(base: Path) -> list[dict]:
    """Scan peer_review_* directories and return metadata.

    Usa find_all_peer_review_dirs (com cache TTL=60s em utils.py) para evitar
    rglob() em cada request. Em repos com muitas análises isso reduz I/O
    de O(n_diretórios) por request para O(1) durante o TTL.
    """
    results = []
    for d in find_all_peer_review_dirs(base):
        files = [f for f in d.glob("*") if f.name != ".checkpoint.json"]
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        n_files = len(files)

        # Checkpoint
        cp_path = d / ".checkpoint.json"
        modules = []
        if cp_path.exists():
            try:
                cp = json.loads(cp_path.read_text(encoding="utf-8"))
                modules = cp.get("completed_modules", [])
            except (json.JSONDecodeError, OSError):
                pass

        # File categories
        csv_files = [f.name for f in files if f.suffix == ".csv"]
        pres_files = [f.name for f in files if f.suffix in (".pptx", ".pdf", ".html")]
        img_files = [f.name for f in files if f.suffix == ".png"]

        results.append({
            "id": d.name,
            "name": d.name.replace("peer_review_", ""),
            "path": str(d),
            "file_count": n_files,
            "size": format_file_size(total_size),
            "modified": datetime.fromtimestamp(d.stat().st_mtime).isoformat(),
            "modules_completed": modules,
            "has_csv": len(csv_files) > 0,
            "has_presentations": [f for f in pres_files if f != "apresentacao_inicial.pdf"],
            "has_artifacts": len(img_files) > 0,
            "csv_files": csv_files,
            "pres_files": pres_files,
            "img_files": img_files,
        })
    return results


def _safe_path(path_str: str) -> Path | None:
    """Validate and resolve a path within BASE_DIR.

    Uses Path.is_relative_to to avoid string-prefix pitfalls like
    "/BASE_DIR-evil" matching "/BASE_DIR" via naive startswith.
    """
    try:
        p = Path(path_str).resolve(strict=False)
        base = BASE_DIR.resolve()
        # Path.is_relative_to is the canonical way (Python 3.9+) and
        # handles symlinks + trailing separators correctly.
        if p.is_relative_to(base) or p == base:
            return p
    except (ValueError, OSError, RuntimeError):
        pass
    return None


# ===== Endpoints =====

@app.get("/api/health")
async def health():
    """Health check."""
    return {
        "status": "ok",
        "version": "7.0.0",
        "pipeline_script": PIPELINE_SCRIPT.exists(),
        "pipeline_running": _any_pipeline_running(),
        "base_dir": str(BASE_DIR),
    }


@app.get("/api/config")
async def get_config():
    """Get available configuration options."""
    return {
        "domains": {
            "res": "🏠 Residencial",
            "com": "🏢 Comercial / Corporativo",
            "mis": "🏗️ Misto (Residencial + Comercial)",
        },
        "modes": {
            "full": "📋 Full — 7 módulos",
            "lite": "⚡ Lite — 5 módulos",
        },
        "max_upload_mb": MAX_UPLOAD_MB,
        "compress_threshold_mb": COMPRESS_THRESHOLD_MB,
        "ocr_threshold_mb": 10,
        "pipeline_running": _any_pipeline_running(),
        "requires_auth": bool(_API_KEY),
    }


@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file for analysis with chunked streaming and automatic Ghostscript compression."""
    valid, msg = await validate_pdf_upload(file)
    if not valid:
        import logging
        logging.getLogger("api").warning(f"Upload rejeitado para '{file.filename}': {msg}")
        raise HTTPException(status_code=400, detail=msg)

    safe_name = sanitize_filename(file.filename or "documento")
    file_path = UPLOAD_DIR / f"{safe_name}.pdf"

    total_bytes = 0
    with open(file_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1 MB chunk streaming
            f.write(chunk)
            total_bytes += len(chunk)

    if total_bytes == 0:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=400, detail="Arquivo enviado está vazio.")

    size_mb = total_bytes / (1024 * 1024)
    if size_mb > MAX_UPLOAD_MB:
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=400,
            detail=f"Arquivo muito grande ({size_mb:.1f} MB). Máximo: {MAX_UPLOAD_MB} MB",
        )

    was_compressed = False
    orig_size_mb = size_mb

    # Otimização automática se o PDF for pesado (> COMPRESS_THRESHOLD_MB, padrão 100 MB)
    if size_mb > COMPRESS_THRESHOLD_MB:
        import logging
        logger = logging.getLogger("api")
        logger.info(f"⚡ PDF pesado detectado no upload ({size_mb:.1f} MB > {COMPRESS_THRESHOLD_MB:.0f} MB). Otimizando via Ghostscript...")
        opt_path = UPLOAD_DIR / f"{safe_name}_opt.pdf"
        try:
            from pipeline.utils import compress_pdf_ghostscript
            success = compress_pdf_ghostscript(str(file_path), str(opt_path))
            if success and opt_path.exists():
                new_size = opt_path.stat().st_size
                new_size_mb = new_size / (1024 * 1024)
                if new_size < total_bytes:
                    opt_path.replace(file_path)
                    total_bytes = new_size
                    size_mb = new_size_mb
                    was_compressed = True
                    reduction_pct = (1 - (new_size / (orig_size_mb * 1024 * 1024))) * 100
                    logger.info(f"  ✅ PDF otimizado no upload: {orig_size_mb:.1f} MB ➔ {size_mb:.1f} MB (redução de {reduction_pct:.1f}%)")
                else:
                    if opt_path.exists():
                        opt_path.unlink()
                    logger.info("  ℹ️ Compressão concluída, mas arquivo original já é menor ou igual.")
            else:
                logger.warning("  ⚠️ Ghostscript não gerou arquivo otimizado. Mantendo original.")
        except Exception as e:
            logger.warning(f"  ⚠️ Falha ao executar otimização no upload: {e}")
            if opt_path.exists():
                opt_path.unlink()

    return {
        "filename": f"{safe_name}.pdf",
        "path": str(file_path),
        "size": total_bytes,
        "size_mb": round(size_mb, 1),
        "safe_name": safe_name,
        "was_compressed": was_compressed,
        "original_size_mb": round(orig_size_mb, 1) if was_compressed else None,
    }



class StartPipelineRequest(BaseModel):
    file_path: str
    domain: str = "res"
    mode: str = "full"
    force: bool = False
    output_dir: str | None = None


@app.post("/api/pipeline/start")
async def start_pipeline(req: StartPipelineRequest):
    """Start the analysis pipeline in background."""
    if _any_pipeline_running():
        raise HTTPException(status_code=409, detail="Um pipeline já está em execução.")

    pdf_path = _safe_path(req.file_path)
    if not pdf_path or not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo PDF não encontrado.")

    size_mb = pdf_path.stat().st_size / (1024 * 1024)
    if size_mb > MAX_UPLOAD_MB:
        raise HTTPException(
            status_code=400,
            detail=f"Arquivo muito grande ({size_mb:.1f} MB). Máx: {MAX_UPLOAD_MB} MB. Use PDF compactado.",
        )
    ocr_warn = size_mb > 10  # >10MB normalmente precisa de OCR no NotebookLM

    # Use provided output_dir or compute default beside the PDF.
    # The pipeline appends peer_review_{safe_name} internally to --output-dir,
    # so we pass the PARENT directory as the base, and store the final path
    # in the registry.
    #
    # When no output_dir is provided:
    #   - If the PDF is inside a subfolder of OUTPUT_BASE_DIR (e.g.
    #     "Arquivos das bancas/Candidato [DSA]/paper.pdf"), use the PDF's
    #     parent dir so peer_review_* lands inside the candidate's folder.
    #   - If the PDF comes from uploads/ (not inside OUTPUT_BASE_DIR),
    #     use OUTPUT_BASE_DIR as fallback.
    safe_name = sanitize_filename(pdf_path.stem)
    if req.output_dir:
        # User provides the PARENT directory; the runner appends
        # peer_review_{safe_name} to --output-dir automatically.
        out_base = str(Path(req.output_dir).resolve())
        final_out = str(Path(out_base) / f"peer_review_{safe_name}")
    else:
        # Default: place output alongside the PDF when it's inside the
        # output tree; otherwise fall back to OUTPUT_BASE_DIR.
        pdf_parent = pdf_path.parent.resolve()
        output_base_resolved = OUTPUT_BASE_DIR.resolve()
        if pdf_parent != output_base_resolved and pdf_parent.is_relative_to(output_base_resolved):
            # PDF is inside a candidate subfolder — output goes there
            out_base = str(pdf_parent)
        else:
            out_base = str(OUTPUT_BASE_DIR)
        final_out = str(Path(out_base) / f"peer_review_{safe_name}")

    pipeline_id = str(uuid.uuid4())
    output_dir = final_out
    _pipeline_registry[pipeline_id] = {
        "status": "running",
        "pipeline_id": pipeline_id,
        "started_at": datetime.now().isoformat(),
        "logs": [],
        "output_dir": final_out,
    }

    def _run():
        try:
            cmd = [
                "python3", "-m", "pipeline.runner",
                str(pdf_path),
                "--domain", req.domain,
                "--mode", req.mode,
                "--force" if req.force else "--resume",
            ]
            if out_base:
                cmd.extend(["--output-dir", out_base])

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1, cwd=APP_DIR,
            )

            logs = []
            for line in process.stdout:
                line = line.strip()
                if line:
                    logs.append(line)
                    _pipeline_registry[pipeline_id]["logs"] = logs
                    _try_update_current_step(pipeline_id, output_dir)

            process.wait()
            _try_update_current_step(pipeline_id, output_dir)
            _pipeline_registry[pipeline_id].update({
                "status": "completed" if process.returncode == 0 else "failed",
                "returncode": process.returncode,
                "finished_at": datetime.now().isoformat(),
            })
        except Exception as e:
            import traceback
            _pipeline_registry[pipeline_id].update({
                "status": "error",
                "error": str(e),
                "error_traceback": traceback.format_exc(),
                "finished_at": datetime.now().isoformat(),
            })

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()

    return {
        "pipeline_id": pipeline_id,
        "status": "running",
        "message": f"{'⚠️ Arquivo grande, pode exigir OCR. ' if ocr_warn else ''}Pipeline iniciado em background.",
        "output_dir": final_out,
    }


@app.get("/api/pipeline/status")
async def pipeline_status():
    """Check if a pipeline is currently running."""
    running = _any_pipeline_running()
    return {"running": running}


def _try_update_current_step(pipeline_id: str, output_dir: str):
    """Read pipeline_status.json from output_dir and update the registry."""
    status_file = Path(output_dir) / "pipeline_status.json"
    try:
        if status_file.exists():
            data = json.loads(status_file.read_text(encoding="utf-8"))
            _pipeline_registry[pipeline_id]["current_step"] = data
            return
        # Fallback: check peer_review_* subdirectory (pipeline with old code)
        parent = Path(output_dir)
        for child in parent.iterdir():
            if child.is_dir() and child.name.startswith("peer_review_"):
                fallback = child / "pipeline_status.json"
                if fallback.exists():
                    data = json.loads(fallback.read_text(encoding="utf-8"))
                    _pipeline_registry[pipeline_id]["current_step"] = data
                    return
    except Exception:
        pass


def _get_progress_data() -> dict:
    """Gather current pipeline progress data (shared by polling + SSE)."""
    running = _any_pipeline_running()
    active = None
    for pid, entry in _pipeline_registry.items():
        if entry.get("status") in ("running",):
            active = entry
            break

    if not active:
        # Return last completed/errored entry if exists (for debugging)
        if _pipeline_registry:
            last_pid = list(_pipeline_registry.keys())[-1]
            last_entry = _pipeline_registry[last_pid]
            result = {"running": False}
            result.update(last_entry)
            return result
        return {"running": False, "status": "idle"}

    # Update step info from filesystem
    output_dir = active.get("output_dir")
    if output_dir:
        _try_update_current_step(active.get("pipeline_id"), output_dir)

    # Compute progress bar stats
    # Pre: 6 steps
    # Modules: 00-07 + bibliography = 9 steps
    # Post: csv + report + artifacts = 3 steps
    TOTAL_STEPS = 18
    completed_mods = []

    if output_dir:
        cp_file = Path(output_dir) / ".checkpoint.json"
        if not cp_file.exists():
            parent = Path(output_dir)
            for child in parent.iterdir():
                if child.is_dir() and child.name.startswith("peer_review_"):
                    fallback = child / ".checkpoint.json"
                    if fallback.exists():
                        cp_file = fallback
                        break
        if cp_file.exists():
            try:
                cp = json.loads(cp_file.read_text(encoding="utf-8"))
                completed_mods = cp.get("completed_modules", [])
            except Exception:
                pass

    # Determine progress from the current step position.
    # The step order matches PIPELINE_STEPS in the frontend.
    _STEP_ORDER = [
        "preflight", "create_notebook", "configure_persona",
        "add_source", "wait_index", "initial_slides",
        "module_00", "module_01", "module_02", "module_03",
        "module_04", "module_05", "module_06", "module_07",
        "bibliography", "csv", "report", "artifacts",
    ]
    current_step_data = active.get("current_step")
    current_step_id = current_step_data.get("step_id", "") if current_step_data else ""
    if current_step_id in _STEP_ORDER:
        # Current step is "running", so completed = its index (0-based = steps before it)
        completed_steps = _STEP_ORDER.index(current_step_id)
    else:
        # Fallback: count completed modules + pre-steps
        completed_steps = len(completed_mods) + 1
    step_percent = round(min(completed_steps / TOTAL_STEPS * 100, 100))

    result = {
        "running": running,
        "pipeline_id": active.get("pipeline_id"),
        "status": active.get("status"),
        "started_at": active.get("started_at"),
        "finished_at": active.get("finished_at"),
        "returncode": active.get("returncode"),
        "error": active.get("error"),
        "current_step": active.get("current_step"),
        "logs": active.get("logs", []),
        "total_steps": TOTAL_STEPS,
        "completed_steps": completed_steps,
        "step_percent": step_percent,
        "completed_modules": completed_mods,
        "output_dir": active.get("output_dir"),
    }

    return result


@app.get("/api/pipeline/progress")
async def pipeline_progress():
    """Get detailed pipeline progress with current step, logs, and module status."""
    return _get_progress_data()


@app.get("/api/pipeline/progress/stream")
async def pipeline_progress_stream():
    """SSE stream: pipeline progress events in real-time (event: progress / heartbeat / done)."""
    async def event_stream():
        last_data = ""
        heartbeat_count = 0
        saw_running = False
        grace_ticks = 0
        MAX_GRACE_TICKS = 10  # wait up to 10s for pipeline to appear
        while True:
            data = _get_progress_data()
            serialized = json.dumps(data, default=str)

            is_running = data.get("running") or data.get("status") == "running"
            if is_running:
                saw_running = True

            # Only send when data changed
            if serialized != last_data:
                yield f"event: progress\ndata: {serialized}\n\n"
                last_data = serialized
                heartbeat_count = 0

            # Pipeline finished — close the stream, but only after we
            # actually saw it running (avoids closing on the very first
            # tick before the pipeline thread has started).
            if not is_running:
                if saw_running:
                    yield f"event: done\ndata: {serialized}\n\n"
                    return
                # Grace period: pipeline may not have appeared yet
                grace_ticks += 1
                if grace_ticks >= MAX_GRACE_TICKS:
                    yield f"event: done\ndata: {serialized}\n\n"
                    return

            # Heartbeat every 15s (keeps nginx/proxy alive)
            heartbeat_count += 1
            if heartbeat_count >= 15:
                yield "event: heartbeat\ndata: {}\n\n"
                heartbeat_count = 0

            await asyncio.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/analyses")
async def list_analyses():
    """List all completed analyses."""
    return _get_analyses(BASE_DIR)


@app.get("/api/analyses/stats")
async def analyses_stats():
    """Aggregated statistics for dashboard charts."""
    base_dir = BASE_DIR
    analyses = []
    # Resume o cache TTL=60s em find_all_peer_review_dirs; parsear MDs é
    # relativamente caro, então evitamos re-rodar por TTL refresh.
    for d in find_all_peer_review_dirs(base_dir):
        # Extract nota from score.json (preferência), com fallback regex no MD
        nota = None

        score_path = d / "score.json"
        if score_path.exists():
            try:
                score_data = json.loads(score_path.read_text(encoding="utf-8"))
                v = score_data.get("nota")
                if isinstance(v, (int, float)):
                    nota = float(v)
            except (json.JSONDecodeError, OSError, ValueError, TypeError):
                nota = None

        if nota is None:
            md06 = d / "06_sintese_parecer.md"
            if md06.exists():
                try:
                    nota = extract_nota_from_synthesis(
                        md06.read_text(encoding="utf-8", errors="replace")
                    )
                except OSError:
                    pass

        # Checkpoint for modules
        cp = d / ".checkpoint.json"
        modules = []
        if cp.exists():
            try:
                cp_data = json.loads(cp.read_text(encoding="utf-8"))
                modules = cp_data.get("completed_modules", [])
            except Exception:
                pass

        files = [f for f in d.glob("*") if f.name != ".checkpoint.json"]
        analyses.append({
            "id": d.name,
            "name": d.name.replace("peer_review_", ""),
            "modified": datetime.fromtimestamp(d.stat().st_mtime).isoformat(),
            "file_count": len(files),
            "total_size": sum(f.stat().st_size for f in files if f.is_file()),
            "modules": len(modules),
            "has_csv": any(f.suffix == ".csv" for f in files),
            "has_pres": any(f.suffix in (".pptx",) for f in files),
            "has_artifacts": any(f.suffix == ".png" for f in files),
            "nota": nota,
        })

    # Timeline: aggregate by month
    from collections import Counter
    monthly = Counter()
    for a in analyses:
        month = a["modified"][:7]  # "2026-07"
        monthly[month] += 1

    timeline = sorted([{"month": m, "count": c} for m, c in monthly.items()], key=lambda x: x["month"])

    valid_notas = [a["nota"] for a in analyses if a["nota"] is not None]

    return {
        "total": len(analyses),
        "with_csv": sum(1 for a in analyses if a["has_csv"]),
        "with_pres": sum(1 for a in analyses if a["has_pres"]),
        "with_artifacts": sum(1 for a in analyses if a["has_artifacts"]),
        "with_nota": len(valid_notas),
        "avg_nota": round(sum(valid_notas) / len(valid_notas), 1) if valid_notas else None,
        "total_files": sum(a["file_count"] for a in analyses),
        "total_size_mb": round(sum(a["total_size"] for a in analyses) / (1024 * 1024), 1),
        "timeline": timeline,
        "notas": [{"name": a["name"], "nota": a["nota"]} for a in analyses if a["nota"] is not None],
        "analyses": [{"name": a["name"], "files": a["file_count"], "modules": a["modules"]} for a in analyses],
    }


@app.get("/api/analyses/compare")
async def compare_analyses(base_id: str = Query(...), target_id: str = Query(...)):
    """Compare two peer-review analyses (e.g. V1 vs V2 or different candidates)."""
    analyses = _get_analyses(BASE_DIR)
    base_info = None
    target_info = None
    for a in analyses:
        if a["id"] == base_id:
            base_info = a
        if a["id"] == target_id:
            target_info = a

    if not base_info or not target_info:
        raise HTTPException(status_code=404, detail="Uma ou ambas as análises não foram encontradas.")

    def _extract_summary(dir_path_str: str) -> dict:
        dp = Path(dir_path_str)
        nota = None
        decisao = "N/A"
        coerencia = None
        fortes = []
        fragilidades = []

        md06 = dp / "06_sintese_parecer.md"
        if md06.exists():
            from utils import extract_structured_score
            struct = extract_structured_score(md06.read_text(encoding="utf-8", errors="ignore"))
            nota = struct.get("nota")
            decisao = struct.get("decisao") or "N/A"
            coerencia = struct.get("coerencia_narrativa")
            fortes = struct.get("pontos_fortes", [])
            fragilidades = struct.get("fragilidades", [])

        erros_count = 0
        csv_file = dp / "tabela_erros.csv"
        if csv_file.exists():
            try:
                import csv
                with open(csv_file, encoding="utf-8", errors="ignore") as f:
                    rows = list(csv.reader(f))
                    erros_count = max(0, len(rows) - 1) if rows else 0
            except Exception:
                pass

        bib_file = dp / "auditoria_bibliografica.json"
        bib_summary = {}
        if bib_file.exists():
            try:
                bib_summary = json.loads(bib_file.read_text(encoding="utf-8"))
            except Exception:
                pass

        return {
            "nota": nota,
            "decisao": decisao,
            "coerencia_narrativa": coerencia,
            "fortes": fortes,
            "fragilidades": fragilidades,
            "erros_count": erros_count,
            "bib_summary": bib_summary,
        }

    base_summary = _extract_summary(base_info["path"])
    target_summary = _extract_summary(target_info["path"])

    delta_nota = None
    if base_summary["nota"] is not None and target_summary["nota"] is not None:
        delta_nota = round(target_summary["nota"] - base_summary["nota"], 2)

    delta_erros = target_summary["erros_count"] - base_summary["erros_count"]

    return {
        "base": {
            "id": base_id,
            "name": base_info["name"],
            **base_summary,
        },
        "target": {
            "id": target_id,
            "name": target_info["name"],
            **target_summary,
        },
        "comparison": {
            "delta_nota": delta_nota,
            "delta_erros": delta_erros,
            "decisao_mudou": base_summary["decisao"] != target_summary["decisao"],
            "evolucao_positiva": (delta_nota > 0 if delta_nota is not None else False) or (delta_erros < 0),
        },
    }


@app.get("/api/analyses/{analysis_id}")
async def get_analysis(analysis_id: str):
    """Get detailed info about a specific analysis."""
    analyses = _get_analyses(BASE_DIR)
    for a in analyses:
        if a["id"] == analysis_id:
            # Full file listing
            dir_path = _safe_path(a["path"])
            if dir_path and dir_path.exists():
                files = []
                for f in sorted(dir_path.glob("*")):
                    if f.name == ".checkpoint.json":
                        continue
                    ext = f.suffix.lstrip(".").lower()
                    icon_map = {"md": "📄", "csv": "📋", "pdf": "📑", "pptx": "📊", "png": "🖼️", "html": "🌐", "json": "📎"}
                    files.append({
                        "name": f.name,
                        "path": str(f),
                        "size": f.stat().st_size,
                        "size_formatted": format_file_size(f.stat().st_size),
                        "extension": ext,
                        "icon": icon_map.get(ext, "📎"),
                        "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                    })
                a["files"] = files

            # Checkpoint
            if dir_path:
                cp = dir_path / ".checkpoint.json"
                if cp.exists():
                    try:
                        a["checkpoint"] = json.loads(cp.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, OSError):
                        pass

            return a

    raise HTTPException(status_code=404, detail="Análise não encontrada.")


@app.get("/api/analyses/{analysis_id}/files/{file_name:path}")
async def get_analysis_file(analysis_id: str, file_name: str):
    """Download or view a specific file from an analysis."""
    analyses = _get_analyses(BASE_DIR)
    base_path = None
    for a in analyses:
        if a["id"] == analysis_id:
            base_path = _safe_path(a["path"])
            break

    if not base_path:
        raise HTTPException(status_code=404, detail="Análise não encontrada.")

    file_path = _safe_path(str(base_path / file_name))
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")

    # Markdown files — return as text
    if file_path.suffix == ".md":
        return JSONResponse({
            "content": file_path.read_text(encoding="utf-8"),
            "name": file_name,
            "type": "markdown",
        })

    # CSV — return as JSON
    if file_path.suffix == ".csv":
        import csv
        rows = []
        with open(file_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            for row in reader:
                rows.append(row)
        return JSONResponse({
            "rows": rows,
            "name": file_name,
            "type": "csv",
        })

    # Images
    if file_path.suffix in (".png", ".jpg", ".jpeg", ".gif", ".webp"):
        return FileResponse(str(file_path), media_type=f"image/{file_path.suffix.lstrip('.')}")

    # JSON
    if file_path.suffix == ".json":
        return JSONResponse({
            "content": json.loads(file_path.read_text(encoding="utf-8")),
            "name": file_name,
            "type": "json",
        })

    # Other binary files (pdf, pptx, html)
    media_map = {
        ".pdf": "application/pdf",
        ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        ".html": "text/html",
        ".txt": "text/plain",
    }
    media_type = media_map.get(file_path.suffix, "application/octet-stream")
    return FileResponse(str(file_path), media_type=media_type, filename=file_name)


@app.get("/api/sources")
async def list_source_pdfs():
    """List uploaded PDFs available for analysis."""
    pdfs = []
    if UPLOAD_DIR.exists():
        for f in sorted(UPLOAD_DIR.glob("*.pdf"), key=lambda x: x.stat().st_mtime, reverse=True):
            pdfs.append({
                "name": f.name,
                "path": str(f),
                "size": format_file_size(f.stat().st_size),
                "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })
    return pdfs


@app.post("/api/analyses/{analysis_id}/rerun")
async def rerun_analysis(analysis_id: str, background_tasks: BackgroundTasks, config: Optional[PipelineConfig] = None):
    """Re-run analysis for an existing PDF."""
    analyses = _get_analyses(BASE_DIR)
    for a in analyses:
        if a["id"] == analysis_id:
            # Try to find original PDF
            pdf_name = a["name"]
            pdf_path = UPLOAD_DIR / f"{pdf_name}.pdf"
            if not pdf_path.exists():
                raise HTTPException(status_code=404, detail="PDF original não encontrado nos uploads.")

            cfg = config or PipelineConfig()
            # Redirect to start_pipeline
            from fastapi.datastructures import FormData
            raise HTTPException(status_code=308, detail="Use POST /api/pipeline/start com file_path do PDF.")

    raise HTTPException(status_code=404, detail="Análise não encontrada.")


@app.delete("/api/analyses/{analysis_id}")
async def delete_analysis(analysis_id: str):
    """Delete an analysis directory."""
    analyses = _get_analyses(BASE_DIR)
    for a in analyses:
        if a["id"] == analysis_id:
            dir_path = _safe_path(a["path"])
            if dir_path and dir_path.exists():
                import shutil
                shutil.rmtree(dir_path)
                return {"status": "deleted", "id": analysis_id}
            raise HTTPException(status_code=404, detail="Diretório não encontrado.")

    raise HTTPException(status_code=404, detail="Análise não encontrada.")


@app.get("/api/browse")
async def browse_directories(path: str = Query(default="")):
    """Browse directories for output selection.

    Returns subdirectories of the given path (or OUTPUT_BASE_DIR if empty).
    Only allows browsing within BASE_DIR for security.
    """
    if not path:
        browse_root = OUTPUT_BASE_DIR.resolve()
    else:
        browse_root = Path(path).resolve()

    # Security: must be within BASE_DIR
    base = BASE_DIR.resolve()
    if not (browse_root == base or browse_root.is_relative_to(base)):
        raise HTTPException(status_code=403, detail="Acesso negado a este diretório.")

    if not browse_root.exists():
        raise HTTPException(status_code=404, detail="Diretório não encontrado.")

    if not browse_root.is_dir():
        raise HTTPException(status_code=400, detail="O caminho não é um diretório.")

    # List only subdirectories (no files, no hidden dirs)
    subdirs = []
    try:
        for entry in sorted(browse_root.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                # Skip internal dirs
                if entry.name in ("__pycache__", "node_modules", ".venv", ".git"):
                    continue
                subdirs.append({
                    "name": entry.name,
                    "path": str(entry),
                    "has_children": any(
                        c.is_dir() and not c.name.startswith(".")
                        for c in entry.iterdir()
                    ) if entry.is_dir() else False,
                })
    except PermissionError:
        raise HTTPException(status_code=403, detail="Sem permissão para ler este diretório.")

    # Compute parent (only if within BASE_DIR)
    parent = None
    if browse_root != base:
        parent_path = browse_root.parent.resolve()
        if parent_path.is_relative_to(base) or parent_path == base:
            parent = str(parent_path)

    return {
        "current": str(browse_root),
        "name": browse_root.name or str(browse_root),
        "parent": parent,
        "directories": subdirs,
    }


@app.get("/api/uploads/{file_name}")
async def get_upload(file_name: str):
    """Download an uploaded PDF."""
    file_path = _safe_path(str(UPLOAD_DIR / file_name))
    if not file_path or not file_path.exists():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado.")
    return FileResponse(str(file_path), media_type="application/pdf", filename=file_name)


# ===== Frontend Static Files (production) =====
_FRONTEND_DIST = APP_DIR / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    # SPA catch-all: serve index.html para qualquer rota não-API
    @app.middleware("http")
    async def serve_frontend(request: Request, call_next):
        path = request.url.path
        # Deixa a API lidar com suas rotas
        if path.startswith("/api/"):
            return await call_next(request)

        # Arquivos estáticos do build
        static_file = _FRONTEND_DIST / path.lstrip("/")
        if static_file.exists() and static_file.is_file():
            media_type = _guess_media_type(static_file.suffix)
            return FileResponse(str(static_file), media_type=media_type)

        # Tudo mais → index.html (SPA)
        index = _FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(str(index), media_type="text/html")

        return await call_next(request)


def _guess_media_type(suffix: str) -> str:
    return {
        ".js": "application/javascript",
        ".css": "text/css",
        ".html": "text/html",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
        ".woff2": "font/woff2",
        ".json": "application/json",
        ".map": "application/json",
    }.get(suffix, "application/octet-stream")


# ===== Entry point =====
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("API_PORT", "8000"))
    host = os.environ.get("API_HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port, log_level="info")
