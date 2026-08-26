"""
Módulo de segurança — sanitização HTML, autenticação, validação de uploads.
"""

import os
import re
import secrets
import hashlib

# ===== HTML Sanitization =====
import bleach

ALLOWED_TAGS = list(bleach.ALLOWED_TAGS) + [
    "p", "br", "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li", "table", "thead", "tbody", "tr", "th", "td",
    "pre", "code", "blockquote", "span", "div", "hr",
]
ALLOWED_ATTRIBUTES = {
    "*": ["class", "id", "style"],
    "a": ["href", "title", "target"],
    "img": ["src", "alt", "width", "height"],
}
ALLOWED_PROTOCOLS = ["http", "https", "mailto"]

def sanitize_html(raw_html: str) -> str:
    """Remove tags e atributos perigosos de HTML usando bleach (XSS prevention).
    
    Requires: pip install bleach>=6.0 (hard dependency)
    """
    if not raw_html:
        return ""
    return bleach.clean(
        raw_html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )


# ===== Password Hashing =====
try:
    import bcrypt

    def hash_password(password: str) -> str:
        """Gera hash bcrypt da senha."""
        salt = bcrypt.gensalt(rounds=12)
        return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

    def verify_password(password: str, hashed: str) -> bool:
        """Verifica senha contra hash bcrypt."""
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except Exception:
            return False

except ImportError:
    import warnings
    warnings.warn(
        "bcrypt não instalado — autenticação usa fallback SHA-256 (MENOS SEGURO). "
        "Instale bcrypt: pip install bcrypt>=4.0",
        RuntimeWarning,
        stacklevel=2,
    )

    def hash_password(password: str) -> str:
        """Fallback: SHA-256 (NÃO recomendado para produção)."""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    def verify_password(password: str, hashed: str) -> bool:
        """Fallback: comparação direta com hash SHA-256."""
        return secrets.compare_digest(hash_password(password), hashed)



# ===== PDF Upload Validation =====
_MAX_UPLOAD_MB_ENV = os.environ.get("MAX_UPLOAD_MB")
MAX_UPLOAD_MB = int(_MAX_UPLOAD_MB_ENV) if _MAX_UPLOAD_MB_ENV else 500
_COMPRESS_THRESHOLD_MB_ENV = os.environ.get("COMPRESS_THRESHOLD_MB")
COMPRESS_THRESHOLD_MB = float(_COMPRESS_THRESHOLD_MB_ENV) if _COMPRESS_THRESHOLD_MB_ENV else 100.0
PDF_MAGIC = b"%PDF"


async def validate_pdf_upload(uploaded_file) -> tuple[bool, str]:
    """Valida que o upload é um PDF autêntico e seguro.

    Returns:
        (is_valid, message)
    """
    if uploaded_file is None:
        return False, "Nenhum arquivo selecionado"

    filename = getattr(uploaded_file, "filename", "") or ""
    if filename and not filename.lower().endswith(".pdf"):
        return False, "O arquivo deve ter a extensão .pdf"

    # Verificar tamanho se informado pelo cliente
    size = getattr(uploaded_file, "size", None)
    if size is not None:
        size_mb = size / (1024 * 1024)
        if size_mb > MAX_UPLOAD_MB:
            return False, f"Arquivo muito grande ({size_mb:.1f} MB). Máximo: {MAX_UPLOAD_MB} MB"
        if size == 0:
            return False, "Arquivo vazio"

    # Ler os primeiros 1024 bytes (conforme norma ISO 32000-1 para PDFs)
    header = await uploaded_file.read(1024)
    try:
        await uploaded_file.seek(0)
    except Exception:
        pass

    if not header:
        return False, "Arquivo vazio"

    if b"%PDF" not in header[:1024]:
        return False, "Arquivo não é um PDF válido (magic bytes inválidos ou cabeçalho %PDF não encontrado)"

    return True, "OK"



# ===== Path Validation =====
def validate_safe_path(path: str, allowed_base: str) -> bool:
    """Valida que um path não foge do diretório base (path traversal prevention)."""
    try:
        resolved = os.path.realpath(path)
        base = os.path.realpath(allowed_base)
        return resolved.startswith(base + os.sep) or resolved == base
    except (ValueError, OSError):
        return False


def get_auth_password() -> str:
    """Obtém a senha de autenticação da variável de ambiente ANALISE_PASSWORD.

    Returns:
        Senha em texto plano.
    """
    return os.environ.get("ANALISE_PASSWORD", "")
