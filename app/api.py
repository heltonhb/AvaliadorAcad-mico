"""
AnaliseTextos API v6.0 — FastAPI REST API para Auditoria Científica e Peer-Review.
"""
# ===== stdlib =====
import asyncio
import base64
import csv
import json
import logging
import os
import re
import shutil
import sys
import time
import uuid
import zipfile
import io
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

# ===== third-party =====
import dotenv
import httpx
import structlog
import uvicorn
from fastapi import FastAPI, Request, Response, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware

dotenv.load_dotenv()

# ===== Telemetry (importado antes do structlog.configure) =====
from telemetry import setup_telemetry, get_tracer

# ===== Logging =====
log_format = os.environ.get("LOG_FORMAT", "text").lower()
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso", utc=False),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer() if log_format == "json" else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# Configurar stdlib logging para capturar logs de bibliotecas
logging.basicConfig(
    level=getattr(logging, log_level, logging.INFO),
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# Silenciar loggers ruidosos de terceiros
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

from auth import (
    create_user,
    authenticate_user,
    create_token,
    verify_token,
    get_user_by_id,
    get_db,
    check_notebooklm_auth,
    get_effective_notebooklm_profile,
    get_notebooklm_profile_path,
    _ensure_db,
    JWT_EXPIRY_HOURS,
)
from security import validate_pdf_upload, validate_safe_path, sanitize_html
from utils import sanitize_filename, find_all_peer_review_dirs, format_file_size, file_icon
from pipeline.constants import APP_DIR, BASE_DIR, CHECKPOINT_FILE, STATUS_FILE
logger = structlog.get_logger("api")

# Telemetry tracer (initialized in lifespan)
_tracer = None
# ===== Constantes =====
DOMAINS = {
    "cs": "Computação",
    "med": "Medicina e Ciências da Saúde",
    "human": "Humanidades e Ciências Sociais",
}
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:8000"
).split(",")

# Configurações de upload
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "500"))

# ===== Rate Limiter =====
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["1000/minute"],  # limite global generoso
    storage_uri=os.environ.get("RATE_LIMIT_STORAGE_URI", "memory://"),
)

# ===== Lifespan =====
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    _ensure_db()

    # Initialize telemetry after app is created
    global _tracer
    _tracer = setup_telemetry(app)

    logger.info("api_startup", version="6.0")
    yield
    # Shutdown
    logger.info("api_shutdown")

# ===== FastAPI App =====
app = FastAPI(
    title="AnaliseTextos API",
    version="6.0",
    description="""
# AnaliseTextos API v6.0

API REST para Auditoria Científica e Peer-Review Acadêmico.

## Funcionalidades Principais
- **Autenticação JWT** com cookies httpOnly
- **Upload seguro de PDF** com validação de magic bytes
- **Pipeline de análise assíncrono** via Celery
- **Health checks** (liveness/readiness) para Kubernetes
- **Rate limiting** por endpoint
- **Structured logging** com correlation IDs
- **OpenTelemetry tracing** (opcional)

## Endpoints Principais
- `/api/auth/*` — Registro, login, logout
- `/api/upload` — Upload de PDFs
- `/api/pipeline/*` — Controle e monitoramento do pipeline
- `/api/analyses/*` — Listagem e consulta de análises
- `/api/health/live` — Liveness probe
- `/api/health/ready` — Readiness probe (DB, NotebookLM, Crossref)
- `/api/config` — Configurações da API

## Autenticação
Use header `Authorization: Bearer <token>` ou cookie `access_token`.
""",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {"name": "auth", "description": "Autenticação e autorização"},
        {"name": "upload", "description": "Upload de documentos"},
        {"name": "pipeline", "description": "Controle do pipeline de análise"},
        {"name": "analyses", "description": "Consulta de análises realizadas"},
        {"name": "health", "description": "Health checks"},
        {"name": "config", "description": "Configurações da API"},
        {"name": "notebooklm", "description": "Integração com NotebookLM"},
        {"name": "sources", "description": "Gerenciamento de fontes PDF"},
        {"name": "browse", "description": "Navegador de diretórios"},
    ],
    lifespan=lifespan,
)

# Rate limiter state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===== Correlation ID Middleware =====
class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Adiciona correlation_id a cada request para tracing."""

    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4())[:8])
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        request.state.correlation_id = correlation_id
        start_time = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time-MS"] = f"{duration_ms:.2f}"
        logger.info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response


app.add_middleware(CorrelationIDMiddleware)

# ===== Auth Middleware =====
class AuthMiddleware(BaseHTTPMiddleware):
    """Verifica JWT cookie ou Bearer token em rotas /api/*."""

    async def dispatch(self, request: Request, call_next):
        # Paths que não exigem autenticação
        public_paths = {
            "/api/health",
            "/api/health/live",
            "/api/health/ready",
            "/api/config",
            "/api/auth/register",
            "/api/auth/login",
            "/api/auth/logout",
            "/api/docs",
            "/api/openapi.json",
        }

        path = request.url.path
        if path in public_paths:
            return await call_next(request)

        # Rotas /api/* protegidas exigem usuário autenticado
        if path.startswith("/api/"):
            token = None
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header[7:]
            elif "access_token" in request.cookies:
                token = request.cookies["access_token"]
            user = None
            if token:
                payload = verify_token(token)
                if payload:
                    user_id = payload.get("sub")
                    if user_id:
                        user = get_user_by_id(int(user_id))

            if not user:
                return JSONResponse({"detail": "Não autenticado"}, status_code=401)

            request.state.user = user
            structlog.contextvars.bind_contextvars(user_id=user["id"], user_email=user["email"])

        return await call_next(request)


app.add_middleware(AuthMiddleware)



# ===== Helpers =====

def _get_user(request: Request) -> dict:
    """Extrai usuário do request.state (set pelo middleware)."""
    return getattr(request.state, "user", None)


def _user_uploads_dir(user_id: int) -> Path:
    """Diretório de uploads isolado por usuário."""
    d = BASE_DIR / "uploads" / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d

def _user_analyses_dir(user_id: int) -> Path:
    """Diretório de análises isolado por usuário."""
    # Usa diretório sem espaços para compatibilidade cross-platform
    analyses_dir_name = os.environ.get("ANALISE_ANALYSES_DIR", "arquivos_bancas")
    d = BASE_DIR / analyses_dir_name / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    return d


# =====================================================================
# AUTH ENDPOINTS
# =====================================================================

class RegisterBody(BaseModel):
    email: str
    password: str
    name: str


class LoginBody(BaseModel):
    email: str
    password: str


# Rate limits from env with defaults
AUTH_RATE_LIMIT = os.environ.get("AUTH_RATE_LIMIT", "10/minute")
UPLOAD_RATE_LIMIT = os.environ.get("UPLOAD_RATE_LIMIT", "30/minute")
PIPELINE_RATE_LIMIT = os.environ.get("PIPELINE_RATE_LIMIT", "5/minute")


@app.post("/api/auth/register")
@limiter.limit(AUTH_RATE_LIMIT)
async def auth_register(request: Request, body: RegisterBody):
    """Cria nova conta de usuário."""
    if os.environ.get("DISABLE_REGISTRATION", "false").lower() == "true":
        raise HTTPException(status_code=403, detail="Novos registros estão desativados")
        
    try:
        user = create_user(body.email, body.password, body.name)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    if not user:
        raise HTTPException(status_code=409, detail="Email já cadastrado")
    token = create_token(user["id"], user["email"])
    response = JSONResponse({"user": user, "access_token": token})
    response.set_cookie(
        key="access_token", value=token, httponly=True,
        samesite="lax", secure=True, max_age=JWT_EXPIRY_HOURS * 3600,
    )
    return response
@app.post("/api/auth/login")
@limiter.limit(AUTH_RATE_LIMIT)
async def auth_login(request: Request, body: LoginBody):
    """Autentica e retorna token JWT em cookie httpOnly e no corpo da resposta."""
    user = authenticate_user(body.email, body.password)
    if not user:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")

    token = create_token(user["id"], user["email"])
    response = JSONResponse({"user": user, "access_token": token})
    response.set_cookie(
        key="access_token", value=token, httponly=True,
        samesite="lax", secure=True, max_age=JWT_EXPIRY_HOURS * 3600,
    )
    return response


@app.get("/api/auth/me")
async def auth_me(request: Request):
    """Retorna dados do usuário logado + status NotebookLM."""
    user = _get_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")
    profile = user.get("notebooklm_profile", "")
    nlm_auth = check_notebooklm_auth(profile) if profile else False
    return {**user, "notebooklm_authenticated": nlm_auth}

# =====================================================================
# HEALTH & CONFIG
# =====================================================================

@app.get("/api/health/live")
async def health_live():
    """Liveness probe — API está rodando."""
    return {"status": "alive", "version": "6.0", "timestamp": datetime.now().isoformat()}


@app.get("/api/health/ready")
async def health_ready():
    """Readiness probe — API pronta para servir tráfego (DB, NotebookLM, Crossref)."""
    checks = {}

    # DB check
    try:
        with get_db() as conn:
            conn.execute("SELECT 1").fetchone()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # NotebookLM CLI check
    try:
        import subprocess
        result = subprocess.run(["notebooklm", "--version"], capture_output=True, timeout=5)
        checks["notebooklm"] = "ok" if result.returncode == 0 else f"error: {result.stderr.decode()[:100]}"
    except Exception as e:
        checks["notebooklm"] = f"error: {e}"

    # Crossref API check (HEAD request, fast)
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.head("https://api.crossref.org/works/10.1000/182")
            checks["crossref"] = "ok" if resp.status_code == 200 else f"http_{resp.status_code}"
    except Exception as e:
        checks["crossref"] = f"error: {e}"

    # Hugging Face Hub check (via hf_integration)
    try:
        from hf_integration import check_hf_setup
        hf = check_hf_setup()
        checks["huggingface"] = hf.get("status", "error")
        if hf.get("user"):
            checks["huggingface"] = f"ok ({hf['user']})"
    except Exception as e:
        checks["huggingface"] = f"error: {e}"

    all_ok = all(v == "ok" or v.startswith("ok") for v in checks.values())
    status_code = 200 if all_ok else 503

    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if all_ok else "degraded",
            "version": "6.0",
            "timestamp": datetime.now().isoformat(),
            "checks": checks,
        },
    )


# Backwards compat
@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "6.0", "timestamp": datetime.now().isoformat()}


@app.get("/api/config")
async def config():
    return {
        "domains": DOMAINS,
        "default_domain": os.environ.get("ANALISE_DEFAULT_DOMAIN", "cs"),
        "default_mode": os.environ.get("ANALISE_DEFAULT_MODE", "full"),
        "max_upload_mb": int(os.environ.get("MAX_UPLOAD_MB", "100")),
        "allowed_origins": ALLOWED_ORIGINS,
    }

# =====================================================================
# UPLOAD
# =====================================================================

@app.post("/api/upload")
@limiter.limit(UPLOAD_RATE_LIMIT)
async def upload(request: Request, file: UploadFile = File(...)):
    """Upload seguro de PDF com validação de magic bytes."""
    user = _get_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")

    # Validar arquivo
    valid, msg = await validate_pdf_upload(file)
    if not valid:
        raise HTTPException(status_code=400, detail=msg)

    # Sanitizar nome
    safe_name = sanitize_filename(file.filename or "documento.pdf")
    if not safe_name.lower().endswith(".pdf"):
        safe_name += ".pdf"

    # Diretório de upload do usuário
    user_upload_dir = _user_uploads_dir(user["id"])
    dest = user_upload_dir / safe_name

    # Evitar sobrescrita
    counter = 1
    orig_dest = dest
    while dest.exists():
        stem = orig_dest.stem
        suffix = orig_dest.suffix
        dest = user_upload_dir / f"{stem}_{counter}{suffix}"
        counter += 1

    # Stream para disco em chunks de 1MB
    total_bytes = 0
    try:
        with open(dest, "wb") as f:
            while chunk := await file.read(1024 * 1024):
                total_bytes += len(chunk)
                size_mb = total_bytes / (1024 * 1024)
                if size_mb > MAX_UPLOAD_MB:
                    f.close()
                    dest.unlink(missing_ok=True)
                    raise HTTPException(status_code=400, detail=f"Arquivo excede {MAX_UPLOAD_MB} MB")
                f.write(chunk)
    except HTTPException:
        raise
    except Exception as e:
        if dest.exists():
            dest.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"Erro ao salvar arquivo: {e}")

    size_mb = round(total_bytes / (1024 * 1024), 2)
    return {
        "filename": file.filename,
        "safe_name": safe_name,
        "path": str(dest),
        "size_mb": size_mb,
        "was_compressed": False,
        "original_size_mb": size_mb,
    }


# =====================================================================
# PIPELINE
# =====================================================================

class PipelineStartBody(BaseModel):
    file_path: str
    domain: str = "cs"
    mode: str = "full"
    force: bool = False
    output_dir: str | None = None


@app.post("/api/pipeline/start")
@limiter.limit(PIPELINE_RATE_LIMIT)
async def pipeline_start(request: Request, body: PipelineStartBody):
    """Inicia pipeline de análise em background via Celery."""
    user = _get_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")

    pdf_path = body.file_path
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="PDF não encontrado")

    user_output_base = _user_analyses_dir(user["id"])
    output_dir = body.output_dir if body.output_dir else str(user_output_base)

    # Build command
    cmd = [
        sys.executable, "-m", "pipeline.runner",
        pdf_path,
        "--domain", body.domain,
        "--mode", body.mode,
        "--output-dir", output_dir,
    ]
    if body.force:
        cmd.append("--force")
    else:
        cmd.append("--resume")

    # Prepare environment
    env = os.environ.copy()
    profile = get_effective_notebooklm_profile(user.get("notebooklm_profile"))
    env["NOTEBOOKLM_PROFILE"] = profile

    # Generate job ID
    job_id = f"job_{uuid.uuid4().hex[:12]}"

    # Create job record in DB
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO pipeline_jobs (id, user_id, pdf_path, domain, mode, force, output_dir, status, celery_task_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (job_id, user["id"], pdf_path, body.domain, body.mode, body.force, output_dir, "pending", None),
        )

    # Enqueue Celery task
    from pipeline.tasks.pipeline_tasks import run_pipeline_task
    from celery_app import EAGER_MODE
    task_id = job_id

    task_args = [job_id, pdf_path, body.domain, body.mode, body.force, output_dir, user["id"], profile]

    if EAGER_MODE:
        # Em modo eager (dev sem worker), task_always_eager executa a task
        # inline e de forma bloqueante. Delegamos para um thread pool gerenciado
        # pelo asyncio para não bloquear o event loop do servidor.
        def _run_eager_sync():
            try:
                run_pipeline_task.apply_async(args=task_args, task_id=job_id)
            except Exception:
                logger.exception("pipeline_eager_failed", job_id=job_id)
                with get_db() as conn:
                    conn.execute(
                        "UPDATE pipeline_jobs SET status='failed', "
                        "error='Falha ao iniciar pipeline (eager mode)', "
                        "updated_at=?, completed_at=? WHERE id=?",
                        (
                            datetime.now(timezone.utc).isoformat(),
                            datetime.now(timezone.utc).isoformat(),
                            job_id,
                        ),
                    )

        loop = asyncio.get_event_loop()
        loop.run_in_executor(None, _run_eager_sync)
    else:
        task = run_pipeline_task.apply_async(args=task_args, task_id=job_id)
        task_id = task.id

    # Update task ID in DB
    with get_db() as conn:
        conn.execute(
            "UPDATE pipeline_jobs SET celery_task_id = ?, status = ?, updated_at = ? WHERE id = ?",
            (task_id, "queued", datetime.now(timezone.utc).isoformat(), job_id),
        )

    pdf_name = Path(pdf_path).stem
    safe_name = re.sub(r"[^\w\-_]", "_", pdf_name)
    final_dir = str(Path(output_dir) / f"peer_review_{safe_name}")

    logger.info("pipeline_queued", job_id=job_id, user_id=user["id"], pdf=pdf_path)
    return {
        "job_id": job_id,
        "output_dir": final_dir,
        "domain": body.domain,
        "mode": body.mode,
        "status": "queued",
    }


@app.get("/api/pipeline/status")
async def pipeline_status(request: Request):
    """Status do job mais recente do usuário."""
    user = _get_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, status, output_dir, created_at, updated_at, completed_at "
            "FROM pipeline_jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user["id"],),
        ).fetchone()

    if not row:
        return {"running": False, "output_dir": None, "status": "idle"}

    return {
        "running": row["status"] in ("pending", "queued", "running"),
        "output_dir": row["output_dir"],
        "status": row["status"],
        "job_id": row["id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "completed_at": row["completed_at"],
    }


@app.get("/api/pipeline/progress")
async def pipeline_progress(request: Request):
    """Lê progresso do pipeline a partir do DB e arquivos de status."""
    user = _get_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Não autenticado")

    with get_db() as conn:
        row = conn.execute(
            "SELECT id, status, progress, output_dir, error "
            "FROM pipeline_jobs WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user["id"],),
        ).fetchone()

    if not row:
        return {"running": False, "status": "idle", "current_step": None, "completed_modules": [], "logs": []}

    job_id = row["id"]
    db_status = row["status"]
    db_progress = row["progress"]
    output_dir = row["output_dir"]
    error = row["error"]

    # Parse progress from DB
    progress_data = {}
    if db_progress:
        try:
            progress_data = json.loads(db_progress)
        except Exception:
            progress_data = {"raw": db_progress}

    # If job is running, also read file-based progress for details
    file_progress = {}
    if output_dir and Path(output_dir).exists():
        file_progress = _read_pipeline_progress(Path(output_dir), user["id"])

    # Combine DB and file progress
    result = {
        "running": db_status in ("pending", "queued", "running"),
        "status": db_status,
        "job_id": job_id,
        "current_step": file_progress.get("current_step"),
        "completed_modules": progress_data.get("completed_modules") or file_progress.get("completed_modules", []),
        "logs": progress_data.get("logs") or file_progress.get("logs", []),
        "output_dir": output_dir,
    }

    if error:
        result["error"] = error

    return result


def _read_pipeline_progress(base_dir: Path, user_id: int) -> dict:
    result = {
        "running": False,
        "status": "idle",
        "current_step": None,
        "completed_modules": [],
        "logs": [],
    }

    # Procura diretório peer_review_* mais recente
    output_dir = None
    if base_dir.exists():
        peer_dirs = sorted(
            [d for d in base_dir.iterdir() if d.is_dir() and d.name.startswith("peer_review_")],
            key=lambda x: x.stat().st_mtime, reverse=True,
        )
        if peer_dirs:
            output_dir = peer_dirs[0]

    if not output_dir:
        return result

    # Lê checkpoint
    checkpoint_file = output_dir / CHECKPOINT_FILE
    if checkpoint_file.exists():
        try:
            cp = json.loads(checkpoint_file.read_text(encoding="utf-8"))
            result["completed_modules"] = cp.get("completed_modules", [])
            result["current_step"] = cp.get("current_step")
            result["status"] = cp.get("status", "running")
            result["running"] = cp.get("status") in ("running", "pending")
        except Exception:
            pass

    # Lê status do pipeline (gravado por pipeline.checkpoint.save_step)
    status_file = output_dir / STATUS_FILE
    if status_file.exists():
        try:
            st = json.loads(status_file.read_text(encoding="utf-8"))
            result["status"] = st.get("status", result["status"])
            result["running"] = st.get("status") in ("running", "pending", "queued")
            if st.get("step_id"):
                result["current_step"] = {
                    "step_id": st["step_id"],
                    "label": st.get("label"),
                }
        except Exception:
            pass

    # Lê logs do pipeline a partir dos arquivos gerados
    result["logs"] = _get_pipeline_logs(output_dir)

    return result



def _get_pipeline_logs(output_dir: Path) -> list[str]:
    """Reconstrói logs a partir dos arquivos gerados."""
    logs = []
    for md in sorted(output_dir.glob("*.md")):
        if md.name != "relatorio_completo.md":
            logs.append(f"✅ {md.name}")
    for f in output_dir.glob("*.csv"):
        logs.append(f"✅ {f.name}")
    for f in output_dir.glob("*.pdf"):
        logs.append(f"✅ {f.name}")
    for f in output_dir.glob("*.html"):
        logs.append(f"✅ {f.name}")
    return logs


@app.get("/api/pipeline/progress/stream")
async def pipeline_progress_stream(request: Request):
    """Server-Sent Events para progresso do pipeline.

    Envia evento 'progress' a cada 3s enquanto o pipeline estiver rodando.
    Envia um 'ping' a cada ciclo para manter a conexão viva em proxies.
    Encerra automaticamente ao detectar desconexão do cliente ou conclusão do job.
    """
    user = _get_user(request)

    async def event_generator():
        consecutive_errors = 0
        while True:
            # Detectar desconexão do cliente antes de processar
            if await request.is_disconnected():
                logger.info("sse_client_disconnected", user_id=user["id"])
                break

            try:
                with get_db() as conn:
                    row = conn.execute(
                        "SELECT id, status, output_dir FROM pipeline_jobs "
                        "WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
                        (user["id"],),
                    ).fetchone()
                consecutive_errors = 0
            except Exception as e:
                consecutive_errors += 1
                logger.warning("sse_db_error", error=str(e), consecutive=consecutive_errors)
                if consecutive_errors >= 3:
                    yield f"event: error\ndata: {json.dumps({'detail': 'Erro interno'})}\n\n"
                    break
                await asyncio.sleep(3)
                continue

            job_status = row["status"] if row else "idle"
            output_dir = row["output_dir"] if row else None

            if output_dir:
                progress = _read_pipeline_progress(Path(output_dir), user["id"])
            else:
                progress = {
                    "running": False, "status": job_status,
                    "current_step": None, "completed_modules": [], "logs": [],
                }
            progress["status"] = job_status
            progress["running"] = job_status in ("pending", "queued", "running")

            # Heartbeat para manter proxies/load balancers acordados
            yield f"event: ping\ndata: {{}}\n\n"
            yield f"event: progress\ndata: {json.dumps(progress, ensure_ascii=False)}\n\n"

            if not progress["running"]:
                yield f"event: done\ndata: {json.dumps(progress, ensure_ascii=False)}\n\n"
                break

            await asyncio.sleep(3)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # desativa buffering no Nginx
        },
    )


# =====================================================================
# ANALYSES
# =====================================================================

@app.get("/api/analyses")
async def list_analyses(request: Request):
    """Lista todas as análises do usuário."""
    user = _get_user(request)
    user_dir = _user_analyses_dir(user["id"])
    return _list_analyses(user_dir)


def _get_analysis_dir(analysis_id: str, user_id: int) -> Path | None:
    """Encontra o diretório da análise pelo ID, buscando APENAS no diretório do usuário.

    A busca é estritamente limitada ao diretório do usuário para evitar que um
    usuário acesse dados de outro (IDOR). O fallback global foi removido.
    """
    # Sanitizar analysis_id para prevenir path traversal
    if not analysis_id or "/" in analysis_id or "\\" in analysis_id or ".." in analysis_id:
        return None
    user_dir = _user_analyses_dir(user_id) / analysis_id
    if user_dir.exists() and user_dir.is_dir():
        return user_dir
    return None


def _list_analyses(user_dir: Path) -> list[dict]:
    """Varre diretórios peer_review_* do usuário e retorna metadados.

    Busca exclusivamente dentro de user_dir para evitar vazamento cross-user.
    """
    dirs = []
    seen = set()

    if not user_dir.exists():
        return dirs

    candidate_dirs = sorted(
        [d for d in user_dir.iterdir() if d.is_dir() and d.name.startswith("peer_review_")],
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )

    for d in candidate_dirs:
        if d.name in seen:
            continue
        seen.add(d.name)
        files = [f for f in d.glob("*") if f.is_file() and not f.name.startswith(".")]
        total_bytes = sum(f.stat().st_size for f in files)
        if total_bytes >= 1024 * 1024:
            size_str = f"{total_bytes / (1024 * 1024):.1f} MB"
        elif total_bytes >= 1024:
            size_str = f"{total_bytes / 1024:.1f} KB"
        else:
            size_str = f"{total_bytes} B"

        # Ler nota do score.json ou parse do 06
        nota = None
        score_file = d / "score.json"
        if score_file.exists():
            try:
                nota = json.loads(score_file.read_text(encoding="utf-8"))["nota"]
            except Exception:
                pass
        if nota is None:
            md_file = d / "06_sintese_parecer.md"
            if md_file.exists():
                try:
                    s_score = extract_structured_score(md_file.read_text(encoding="utf-8", errors="replace"))
                    nota = s_score.get("nota")
                except Exception:
                    pass

        # Módulos concluídos
        completed_mods = []
        for m in sorted(d.glob("[0-9][0-9]_*.md")):
            completed_mods.append(m.name[:2])

        dirs.append({
            "id": d.name,
            "name": d.name.replace("peer_review_", "").replace("_", " "),
            "file_count": len(files),
            "size": size_str,
            "modified": datetime.fromtimestamp(d.stat().st_mtime).isoformat(),
            "nota": nota,
            "modules_completed": completed_mods,
            "path": str(d),
        })
    return dirs


@app.get("/api/analyses/stats")
async def analyses_stats(request: Request):
    """Estatísticas agregadas das análises do usuário."""
    user = _get_user(request)
    user_dir = _user_analyses_dir(user["id"])
    analyses = _list_analyses(user_dir)

    total = len(analyses)
    with_csv = sum(1 for a in analyses if _has_file(user_dir / a["id"], "csv"))
    with_pres = sum(1 for a in analyses if _has_file(user_dir / a["id"], "pdf", "pptx", "html"))

    # Timeline (análises por mês)
    timeline = {}
    for a in analyses:
        try:
            dt = datetime.fromisoformat(a["modified"])
            month_key = dt.strftime("%Y-%m")
            timeline[month_key] = timeline.get(month_key, 0) + 1
        except Exception:
            pass
    timeline_list = [{"month": k, "count": v} for k, v in sorted(timeline.items())]

    # Notas
    notas = []
    for a in analyses:
        if a.get("nota") is not None:
            notas.append({"name": a["name"][:20], "nota": a["nota"]})

    # Detalhes por análise
    analysis_details = []
    for a in analyses[:10]:
        d = user_dir / a["id"]
        md_count = len(list(d.glob("*.md")))
        analysis_details.append({
            "name": a["name"][:15],
            "files": a["file_count"],
            "modules": md_count,
        })

    return {
        "total": total,
        "with_csv": with_csv,
        "with_pres": with_pres,
        "timeline": timeline_list,
        "notas": notas,
        "analyses": analysis_details,
    }


def _has_file(d: Path, *extensions: str) -> bool:
    for ext in extensions:
        if list(d.glob(f"*.{ext}")):
            return True
    return False


@app.get("/api/analyses/compare")
async def compare_analyses(request: Request, base_id: str, target_id: str):
    """Compara duas análises (delta de nota, decisão, erros)."""
    user = _get_user(request)
    user_dir = _user_analyses_dir(user["id"])
    base_dir = user_dir / base_id
    target_dir = user_dir / target_id

    if not base_dir.exists():
        raise HTTPException(status_code=404, detail=f"Análise base '{base_id}' não encontrada")
    if not target_dir.exists():
        raise HTTPException(status_code=404, detail=f"Análise alvo '{target_id}' não encontrada")

    base_score = _load_score(base_dir)
    target_score = _load_score(target_dir)

    base_errors = _count_csv_errors(base_dir)
    target_errors = _count_csv_errors(target_dir)

    delta_nota = None
    if base_score.get("nota") is not None and target_score.get("nota") is not None:
        delta_nota = round(target_score["nota"] - base_score["nota"], 2)

    return {
        "base": {"id": base_id, **base_score, "error_count": base_errors},
        "target": {"id": target_id, **target_score, "error_count": target_errors},
        "delta_nota": delta_nota,
        "delta_errors": target_errors - base_errors if base_errors is not None and target_errors is not None else None,
        "improved": delta_nota is not None and delta_nota > 0,
    }


def _load_score(d: Path) -> dict:
    """Carrega score.json ou faz parse do módulo 06."""
    score_file = d / "score.json"
    if score_file.exists():
        try:
            return json.loads(score_file.read_text(encoding="utf-8"))
        except Exception:
            pass
    # Fallback: parsear 06_sintese_parecer.md
    md_file = d / "06_sintese_parecer.md"
    if md_file.exists():
        try:
            text = md_file.read_text(encoding="utf-8", errors="replace")
            return extract_structured_score(text)
        except Exception:
            pass
    return {"nota": None, "decisao": None}


def _count_csv_errors(d: Path) -> int | None:
    csv_file = d / "tabela_erros.csv"
    if not csv_file.exists():
        return None
    try:
        with open(csv_file, "r", encoding="utf-8") as f:
            return max(0, sum(1 for _ in f) - 1)  # -1 para header
    except Exception:
        return None


@app.get("/api/analyses/{analysis_id}")
async def get_analysis(analysis_id: str, request: Request):
    """Detalhe de uma análise com lista de arquivos."""
    user = _get_user(request)
    analysis_dir = _get_analysis_dir(analysis_id, user["id"])
    if not analysis_dir or not analysis_dir.exists():
        raise HTTPException(status_code=404, detail="Análise não encontrada")

    files_info = []
    for f in sorted(analysis_dir.glob("*")):
        if f.is_file() and not f.name.startswith("."):
            ext = f.suffix.lstrip(".")
            files_info.append({
                "name": f.name,
                "extension": ext,
                "size": f.stat().st_size,
                "size_formatted": format_file_size(f.stat().st_size),
                "icon": file_icon(ext),
            })

    return {
        "id": analysis_id,
        "name": analysis_id.replace("peer_review_", "").replace("_", " "),
        "file_count": len(files_info),
        "files": files_info,
        "modified": datetime.fromtimestamp(analysis_dir.stat().st_mtime).isoformat(),
        "path": str(analysis_dir),
    }


@app.get("/api/analyses/{analysis_id}/files/{filename}")
async def get_analysis_file(analysis_id: str, filename: str, request: Request):
    """Serve arquivo da análise: MD como JSON, CSV como JSON rows, outros como download."""
    user = _get_user(request)
    analysis_dir = _get_analysis_dir(analysis_id, user["id"])
    if not analysis_dir or not analysis_dir.exists():
        raise HTTPException(status_code=404, detail="Análise não encontrada")

    # Sanitização preemptiva: rejeitar qualquer tentativa de path traversal
    # antes mesmo de construir o caminho no disco.
    if not filename or "/" in filename or "\\" in filename or ".." in filename or "\x00" in filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido")

    file_path = analysis_dir / filename
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # Segunda linha de defesa: confirmar que o path resolvido está dentro do diretório
    try:
        file_path.resolve().relative_to(analysis_dir.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Acesso negado")

    ext = file_path.suffix.lstrip(".").lower()

    # Markdown → JSON com conteúdo
    if ext == "md":
        content = file_path.read_text(encoding="utf-8", errors="replace")
        return {"name": filename, "content": sanitize_html(content)}

    # CSV → JSON com rows
    if ext == "csv":
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)
            return {"name": filename, "rows": rows}
        except Exception:
            return {"name": filename, "rows": []}

    # JSON → retorna direto
    if ext == "json":
        try:
            data = json.loads(file_path.read_text(encoding="utf-8"))
            return data
        except Exception:
            raise HTTPException(status_code=500, detail="JSON inválido")

    # Binários (PDF, PPTX, HTML, PNG) → FileResponse
    media_types = {
        "pdf": "application/pdf",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
        "html": "text/html",
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
    }
    return FileResponse(
        str(file_path),
        media_type=media_types.get(ext, "application/octet-stream"),
        filename=filename,
    )


@app.delete("/api/analyses/{analysis_id}")
async def delete_analysis(analysis_id: str, request: Request):
    """Remove diretório de análise."""
    user = _get_user(request)
    analysis_dir = _get_analysis_dir(analysis_id, user["id"])
    if not analysis_dir or not analysis_dir.exists():
        raise HTTPException(status_code=404, detail="Análise não encontrada")

    # Validação de segurança antes de apagar
    try:
        analysis_dir.resolve().relative_to(BASE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Acesso negado")

    shutil.rmtree(analysis_dir)
    return {"ok": True, "deleted": analysis_id}


@app.get("/api/analyses/{analysis_id}/download")
async def download_analysis_zip(analysis_id: str, request: Request, cleanup: bool = False):
    """Empacota todos os artefatos da análise em um ZIP e retorna para download.
    Se cleanup=true, remove os arquivos do servidor após gerar o ZIP."""
    user = _get_user(request)
    analysis_dir = _get_analysis_dir(analysis_id, user["id"])
    if not analysis_dir or not analysis_dir.exists():
        raise HTTPException(status_code=404, detail="Análise não encontrada")

    # Validação anti path-traversal
    try:
        analysis_dir.resolve().relative_to(BASE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Acesso negado")

    # Gerar ZIP em memória
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(analysis_dir.rglob("*")):
            if file_path.is_file() and not file_path.name.startswith("."):
                arcname = str(file_path.relative_to(analysis_dir.parent))
                zf.write(file_path, arcname)

    zip_buffer.seek(0)
    zip_filename = f"{analysis_id}.zip"

    # Limpar arquivos do servidor após gerar o ZIP (se solicitado)
    if cleanup:
        try:
            shutil.rmtree(analysis_dir)
            logger.info("analysis_cleanup", analysis_id=analysis_id, user_id=user["id"])
        except Exception as e:
            logger.warning("analysis_cleanup_failed", analysis_id=analysis_id, error=str(e))

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{zip_filename}"'},
    )


# =====================================================================
# OBSIDIAN EXPORT
# =====================================================================

class ObsidianExportBody(BaseModel):
    vault_path: str


def _add_yaml_frontmatter(content: str, analysis_name: str, filename: str, score_data: dict | None = None) -> str:
    """Adiciona YAML frontmatter a um arquivo Markdown para compatibilidade com Obsidian."""
    tags = ["analisetextos", "peer-review"]
    # Adiciona tags baseado no nome do arquivo
    name_lower = filename.lower()
    if "metodologia" in name_lower:
        tags.append("metodologia")
    if "escrita" in name_lower:
        tags.append("escrita")
    if "gaps" in name_lower:
        tags.append("gaps")
    if "parecer" in name_lower or "sintese" in name_lower:
        tags.append("parecer")
    if "auditoria" in name_lower:
        tags.append("auditoria")
    if "estrutura" in name_lower:
        tags.append("estrutura")
    if "referencial" in name_lower or "sota" in name_lower:
        tags.append("referencial")

    frontmatter_lines = [
        "---",
        f"title: \"{filename.replace('.md', '').replace('_', ' ').title()}\"",
        f"source: \"AnaliseTextos\"",
        f"analysis: \"{analysis_name}\"",
        f"date: \"{datetime.now().strftime('%Y-%m-%d')}\"",
        f"tags: [{', '.join(tags)}]",
    ]

    if score_data:
        if score_data.get("nota"):
            frontmatter_lines.append(f"nota: {score_data['nota']}")
        if score_data.get("decision"):
            frontmatter_lines.append(f"decision: \"{score_data['decision']}\"")
        if score_data.get("contribution_level"):
            frontmatter_lines.append(f"contribution_level: \"{score_data['contribution_level']}\"")

    frontmatter_lines.append("---")
    frontmatter_lines.append("")

    return "\n".join(frontmatter_lines) + content


@app.post("/api/analyses/{analysis_id}/export/obsidian")
async def export_to_obsidian(analysis_id: str, body: ObsidianExportBody, request: Request):
    """Exporta todos os arquivos da análise para um vault do Obsidian.

    Cria uma subpasta 'AnaliseTextos/{analysis_name}/' dentro do vault.
    Arquivos .md recebem YAML frontmatter com tags e metadados.
    Cria um arquivo 00_MOC.md como índice (Map of Content).
    """
    user = _get_user(request)
    analysis_dir = _get_analysis_dir(analysis_id, user["id"])
    if not analysis_dir or not analysis_dir.exists():
        raise HTTPException(status_code=404, detail="Análise não encontrada")

    vault_path = Path(body.vault_path).expanduser().resolve()

    # Validar que o vault existe e contém .obsidian/
    if not vault_path.exists():
        raise HTTPException(status_code=400, detail="Diretório do vault não encontrado")
    if not (vault_path / ".obsidian").is_dir():
        raise HTTPException(status_code=400, detail="Diretório não parece ser um vault do Obsidian (pasta .obsidian não encontrada)")

    # Validar segurança: vault deve estar em local razoável
    try:
        vault_path.relative_to(Path.home().resolve())
    except ValueError:
        # Permite paths fora do home, mas valida que não é path-traversal malicioso
        if ".." in body.vault_path or "~" in body.vault_path:
            raise HTTPException(status_code=403, detail="Path não permitido")

    # Criar subpasta da análise no vault
    analysis_name = analysis_dir.name
    export_dir = vault_path / "AnaliseTextos" / analysis_name
    export_dir.mkdir(parents=True, exist_ok=True)

    # Ler score.json se existir (para frontmatter)
    score_data = None
    score_file = analysis_dir / "score.json"
    if score_file.exists():
        try:
            score_data = json.loads(score_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    # Copiar todos os arquivos
    file_count = 0
    md_files = []

    for file_path in sorted(analysis_dir.rglob("*")):
        if not file_path.is_file() or file_path.name.startswith("."):
            continue

        dest = export_dir / file_path.name

        if file_path.suffix == ".md":
            # Adicionar frontmatter YAML
            content = file_path.read_text(encoding="utf-8")
            enriched = _add_yaml_frontmatter(content, analysis_name, file_path.name, score_data)
            dest.write_text(enriched, encoding="utf-8")
            md_files.append(file_path.name)
        else:
            # Copiar binários e outros formatos
            shutil.copy2(file_path, dest)

        file_count += 1

    # Criar MOC (Map of Content)
    moc_lines = [
        "---",
        f"title: \"Mapa de Conteúdo - {analysis_name}\"",
        "source: \"AnaliseTextos\"",
        f"analysis: \"{analysis_name}\"",
        f"date: \"{datetime.now().strftime('%Y-%m-%d')}\"",
        "tags: [analisetextos, moc, peer-review]",
        "---",
        "",
        f"# Mapa de Conteúdo — {analysis_name}",
        "",
        "## Relatórios",
        "",
    ]

    # Ordem dos relatórios
    report_order = [
        ("00_estrutura_documento.md", "📋 Estrutura do Documento"),
        ("01_auditoria_metodologica.md", "🔍 Auditoria Metodológica"),
        ("02_checklist_editorial.md", "✅ Checklist Editorial"),
        ("03_referencial_teorico.md", "📚 Referencial Teórico"),
        ("04_gaps_logicos.md", "⚠️ Gaps Lógicos"),
        ("05_analise_escrita.md", "✍️ Análise de Escrita"),
        ("06_sintese_parecer.md", "📝 Síntese e Parecer"),
        ("07_auditoria_quantitativa.md", "📊 Auditoria Quantitativa"),
    ]

    exported_names = {f.replace(".md", "") for f in md_files}

    for filename, label in report_order:
        name_no_ext = filename.replace(".md", "")
        if name_no_ext in exported_names:
            moc_lines.append(f"- [[{filename.replace('.md', '')}|{label}]]")

    # Adicionar outros arquivos .md que não estão na ordem padrão
    standard_names = {f.replace(".md", "") for f, _ in report_order}
    for md_file in sorted(md_files):
        name_no_ext = md_file.replace(".md", "")
        if name_no_ext not in standard_names:
            moc_lines.append(f"- [[{name_no_ext}|{md_file.replace('.md', '').replace('_', ' ').title()}]]")

    # Adicionar outros arquivos
    other_files = [
        f for f in sorted(analysis_dir.iterdir())
        if f.is_file() and not f.name.startswith(".") and f.suffix != ".md"
    ]

    if other_files:
        moc_lines.extend(["", "## Outros Arquivos", ""])
        for f in other_files:
            moc_lines.append(f"- {f.name}")

    if score_data:
        moc_lines.extend([
            "",
            "## Score",
            "",
            f"- **Nota:** {score_data.get('nota', 'N/A')}",
            f"- **Decisão:** {score_data.get('decision', 'N/A')}",
            f"- **Nível de Contribuição:** {score_data.get('contribution_level', 'N/A')}",
        ])

    moc_content = "\n".join(moc_lines) + "\n"
    (export_dir / "00_MOC.md").write_text(moc_content, encoding="utf-8")
    file_count += 1

    logger.info(
        "obsidian_export",
        analysis_id=analysis_id,
        user_id=user["id"],
        vault_path=str(vault_path),
        file_count=file_count,
    )

    return {
        "ok": True,
        "exported_path": str(export_dir),
        "file_count": file_count,
        "vault_path": str(vault_path),
    }


# =====================================================================
# SOURCES & BROWSE
# =====================================================================

@app.get("/api/sources")
async def list_sources(request: Request):
    """Lista PDFs enviados pelo usuário."""
    user = _get_user(request)
    upload_dir = _user_uploads_dir(user["id"])
    files = []
    for f in sorted(upload_dir.glob("*.pdf"), key=lambda x: x.stat().st_mtime, reverse=True):
        files.append({
            "name": f.name,
            "path": str(f),
            "size": format_file_size(f.stat().st_size),
            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return files


class MkdirBody(BaseModel):
    path: str


@app.post("/api/browse/mkdir")
async def browse_mkdir(body: MkdirBody, request: Request):
    """Cria uma nova pasta dentro de BASE_DIR."""
    user = _get_user(request)
    target = Path(body.path).resolve()

    try:
        target.relative_to(BASE_DIR.resolve())
    except ValueError:
        raise HTTPException(status_code=403, detail="Acesso negado fora do diretório base")

    try:
        target.mkdir(parents=True, exist_ok=True)
        return {"ok": True, "path": str(target)}
    except OSError as e:
        raise HTTPException(status_code=400, detail=f"Erro ao criar pasta: {e}")


@app.get("/api/browse")
async def browse(request: Request, path: str = ""):
    """Navegador de diretórios (dentro do BASE_DIR)."""
    user = _get_user(request)
    user_base = _user_analyses_dir(user["id"])

    if path and path.strip():
        target = Path(path).resolve()
    else:
        target = user_base

    # Validação anti path-traversal — permite navegar dentro do BASE_DIR ou user_base
    try:
        target.resolve().relative_to(BASE_DIR.resolve())
    except ValueError:
        try:
            target.resolve().relative_to(user_base.resolve())
        except ValueError:
            raise HTTPException(status_code=403, detail="Acesso negado a este diretório")

    if not target.exists() or not target.is_dir():
        if target == user_base:
            user_base.mkdir(parents=True, exist_ok=True)
        else:
            raise HTTPException(status_code=404, detail="Diretório não encontrado")

    is_root = (target.resolve() == BASE_DIR.resolve())
    parent_path = str(target.parent) if not is_root and target.parent.resolve() >= BASE_DIR.resolve() else None

    directories = []
    entries = []
    try:
        for item in sorted(target.iterdir()):
            if item.name.startswith("."):
                continue
            is_directory = item.is_dir()
            has_children = False
            if is_directory:
                try:
                    has_children = any(c.is_dir() for c in item.iterdir() if not c.name.startswith("."))
                except (PermissionError, OSError):
                    has_children = False
                directories.append({
                    "name": item.name,
                    "path": str(item),
                    "is_dir": True,
                    "has_children": has_children,
                })
            entries.append({
                "name": item.name,
                "path": str(item),
                "is_dir": is_directory,
                "size": format_file_size(item.stat().st_size) if item.is_file() else None,
            })
    except (PermissionError, OSError) as e:
        raise HTTPException(status_code=403, detail=f"Sem permissão para ler o diretório: {e}")

    return {
        "current": str(target),
        "path": str(target),
        "name": target.name or str(target),
        "parent": parent_path,
        "directories": directories,
        "entries": entries,
    }


# =====================================================================
# NOTEBOOKLM AUTH
# =====================================================================

@app.get("/api/notebooklm/auth/status")
async def notebooklm_auth_status(request: Request):
    """Verifica se o usuário está autenticado com NotebookLM."""
    user = _get_user(request)
    profile = user.get("notebooklm_profile", "")
    effective_profile = get_effective_notebooklm_profile(profile)
    profile_path = get_notebooklm_profile_path(effective_profile)
    storage_path = profile_path / "storage_state.json"

    if storage_path.exists():
        return {"authenticated": True, "profile": effective_profile}
    else:
        target_profile = profile or "default"
        return {
            "authenticated": False,
            "profile": target_profile,
            "detail": f"Não autenticado. Execute: notebooklm login --profile {target_profile}",
        }


@app.get("/api/notebooklm/account/info")
async def notebooklm_account_info(request: Request):
    """Informações da conta NotebookLM do usuário."""
    user = _get_user(request)
    profile = user.get("notebooklm_profile", "")
    effective_profile = get_effective_notebooklm_profile(profile)
    profile_path = get_notebooklm_profile_path(effective_profile)
    storage_path = profile_path / "storage_state.json"

    if not storage_path.exists():
        target_profile = profile or "default"
        return {
            "authenticated": False,
            "profile": target_profile,
            "message": f"Não autenticado. Execute: notebooklm login --profile {target_profile}",
            "instructions": (
                f"Para autenticar com NotebookLM, execute o comando:\n\n"
                f"  notebooklm login --profile {target_profile}\n\n"
                "Isso abrirá um navegador para login com sua conta Google."
            ),
        }

    # Tentar extrair info da conta (suporta formato NotebookLM 0.8+)
    try:
        data = json.loads(storage_path.read_text(encoding="utf-8"))
        account = (
            data.get("notebooklm", {}).get("account", {}).get("email")
            or data.get("email")
            or data.get("user", {}).get("email")
            or "unknown"
        )
        return {
            "authenticated": True,
            "account": account,
            "profile": effective_profile,
            "message": f"Logado como {account}",
        }
    except Exception:
        return {
            "authenticated": True,
            "account": "unknown",
            "profile": effective_profile,
            "message": "Autenticado",
        }


@app.post("/api/notebooklm/auth/login")
async def notebooklm_auth_login(request: Request):
    """Instruções para autenticar com NotebookLM."""
    user = _get_user(request)
    profile = user.get("notebooklm_profile", "default")
    return {
        "detail": (
            f"Para autenticar com NotebookLM, execute:\n\n"
            f"  notebooklm login --profile {profile}\n\n"
            "Isso abrirá um navegador para login com sua conta Google."
        ),
    }


# =====================================================================
# STATIC FILES (Production — serve frontend build)
# =====================================================================

_frontend_dist = APP_DIR / "frontend" / "dist"
if _frontend_dist.exists():
    # Catch-all SPA route — DEVE vir antes do mount estático
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve index.html para rotas SPA não-API."""
        # Não interceptar rotas /api
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404)
        # Tentar servir arquivo estático primeiro
        static_file = _frontend_dist / full_path
        if static_file.exists() and static_file.is_file():
            return FileResponse(str(static_file))
        # Fallback para index.html (SPA routing)
        index = _frontend_dist / "index.html"
        if index.exists():
            return FileResponse(str(index))
        raise HTTPException(status_code=404, detail="Frontend não construído")


# Restaurar storage_state.json a partir de variável de ambiente (deploy sem volume)
env_b64 = os.environ.get("NOTEBOOKLM_STORAGE_STATE_BASE64")
if env_b64:
    try:
        profile_path = get_notebooklm_profile_path("default")
        profile_path.mkdir(parents=True, exist_ok=True)
        storage_file = profile_path / "storage_state.json"
        decoded = base64.b64decode(env_b64).decode("utf-8")
        storage_file.write_text(decoded, encoding="utf-8")
        logger.info("Restaurado storage_state.json a partir da variável NOTEBOOKLM_STORAGE_STATE_BASE64")
    except Exception as e:
        logger.error(f"Falha ao restaurar storage_state.json: {e}")

# =====================================================================
# MAIN
# =====================================================================

if __name__ == "__main__":
    port = int(os.environ.get("API_PORT", "8000"))
    logger.info(f"🚀 AnaliseTextos API v6.0 — http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")