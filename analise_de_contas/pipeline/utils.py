"""Utilitários do pipeline: execução segura de comandos e OCR check."""
import os
import subprocess
import tempfile
from pathlib import Path


def run_cmd(cmd, timeout=None, cwd=None):
    """Executa comando externo de forma segura (shell=False).

    Args:
        cmd: Lista de argumentos [comando, arg1, arg2, ...]
        timeout: Timeout em segundos (default: RUN_CMD_TIMEOUT env ou 300)
        cwd: Diretório de trabalho opcional

    Returns:
        (stdout, stderr, returncode) — sempre strings

    Raises:
        TypeError: Se cmd for string (não lista)
    """
    if timeout is None:
        timeout = int(os.environ.get("RUN_CMD_TIMEOUT", "300"))
    if isinstance(cmd, str):
        raise TypeError("run_cmd recebeu string — use uma lista de argumentos")
    try:
        r = subprocess.run(
            cmd, shell=False, capture_output=True, text=True,
            timeout=timeout, cwd=cwd,
        )
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", "Timeout", 1
    except Exception as e:
        return "", str(e), 1


def check_ocr_needed(pdf_path: str, min_chars: int = 100) -> bool:
    """Verifica se PDF precisa de OCR (pouco texto extraível)."""
    import tempfile
    import subprocess
    tmp = tempfile.mktemp(suffix=".txt")
    try:
        subprocess.run(
            ["pdftotext", str(pdf_path), tmp],
            capture_output=True, text=True, timeout=30,
        )
        if os.path.exists(tmp):
            text = Path(tmp).read_text(encoding="utf-8", errors="replace")
            return len(text.strip()) < min_chars
        return True
    except Exception as e:
        import logging
        logging.getLogger("pipeline").warning(f"Falha ao verificar OCR: {e}")
        return False
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def compress_pdf_ghostscript(
    input_pdf: str,
    output_pdf: str,
    pdf_setting: str = "/ebook",
    timeout: int = 300,
) -> bool:
    """Executa compressão de PDF via Ghostscript (otimizando imagens para ~150 DPI mantendo texto vetorial).

    Comando executado:
        gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS={pdf_setting} -dNOPAUSE -dQUIET -dBATCH -sOutputFile={output_pdf} {input_pdf}
    """
    cmd = [
        "gs",
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={pdf_setting}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={output_pdf}",
        str(input_pdf),
    ]
    _, stderr, code = run_cmd(cmd, timeout=timeout)
    return code == 0 and os.path.exists(output_pdf) and os.path.getsize(output_pdf) > 0


def compress_pdf_if_large(
    pdf_path: str,
    output_dir: Path,
    threshold_mb: float = 100.0,
) -> tuple[str, bool]:
    """Verifica se o PDF excede o threshold_mb e, caso afirmativo, gera versão otimizada via Ghostscript.

    Retorna:
        (caminho_final_do_pdf, foi_comprimido)
    """
    pdf_p = Path(pdf_path)
    if not pdf_p.exists():
        return pdf_path, False

    size_bytes = pdf_p.stat().st_size
    size_mb = size_bytes / (1024 * 1024)

    if size_mb <= threshold_mb:
        return pdf_path, False

    optimized_pdf = output_dir / f"{pdf_p.stem}_otimizado.pdf"

    import logging
    logger = logging.getLogger("pipeline")
    logger.info(f"\n⚡ PDF pesado detectado ({size_mb:.1f} MB > {threshold_mb:.0f} MB). Otimizando via Ghostscript...")

    success = compress_pdf_ghostscript(str(pdf_p), str(optimized_pdf))
    if success and optimized_pdf.exists():
        new_size_bytes = optimized_pdf.stat().st_size
        new_size_mb = new_size_bytes / (1024 * 1024)
        reduction_pct = (1 - (new_size_bytes / size_bytes)) * 100 if size_bytes > 0 else 0
        logger.info(f"  ✅ PDF otimizado com sucesso: {size_mb:.1f} MB ➔ {new_size_mb:.1f} MB (redução de {reduction_pct:.1f}%)")
        return str(optimized_pdf), True
    else:
        logger.warning("  ⚠️ Falha ao otimizar PDF com Ghostscript. Prosseguindo com original.")
        return pdf_path, False

