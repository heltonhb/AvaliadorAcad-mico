"""
Módulo de autenticação — usuários, sessões JWT e banco SQLite.
"""
import os
import re
import hashlib
import secrets
import sqlite3
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from contextlib import contextmanager

try:
    import jwt  # PyJWT
except ImportError:
    jwt = None

from security import hash_password, verify_password

_logger = logging.getLogger("auth")
# ===== Configurações =====
DB_PATH = os.environ.get("DB_PATH", str(Path(__file__).parent / "data" / "users.db"))

# JWT_SECRET é OBRIGATÓRIO em produção. Em dev, gera um temporário com warning.
_jwt_secret_env = os.environ.get("JWT_SECRET")
if _jwt_secret_env:
    JWT_SECRET = _jwt_secret_env
else:
    import warnings
    warnings.warn(
        "JWT_SECRET não definido em variável de ambiente. "
        "Gerando segredo temporário — tokens serão invalidados no próximo restart. "
        "Defina JWT_SECRET no .env para produção (openssl rand -hex 32).",
        RuntimeWarning,
        stacklevel=2,
    )
    JWT_SECRET = secrets.token_hex(32)

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.environ.get("JWT_EXPIRY_HOURS", "24"))


# ===== Database =====

def _ensure_db():
    """Cria o diretório e o banco se não existirem. Habilita WAL mode para concorrência."""
    db_path = Path(DB_PATH)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            name TEXT NOT NULL,
            notebooklm_profile TEXT DEFAULT 'default',
            last_login TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pipeline_jobs (
            id TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            pdf_path TEXT NOT NULL,
            domain TEXT NOT NULL,
            mode TEXT NOT NULL,
            force BOOLEAN DEFAULT 0,
            output_dir TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            progress TEXT,
            error TEXT,
            celery_task_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_user ON pipeline_jobs(user_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_pipeline_jobs_status ON pipeline_jobs(status)")
    conn.commit()
    conn.close()

@contextmanager
def get_db():
    """Context manager para conexão SQLite com row_factory e WAL."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA busy_timeout=5000")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()



# ===== Operações de Usuário =====

def create_user(email: str, password: str, name: str) -> dict | None:
    """Cria um novo usuário. Retorna dict do usuário ou None se já existe."""
    email = email.strip().lower()
    if not re.match(r'^[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}$', email):
        raise ValueError("Email inválido")
    if len(password) < 6:
        raise ValueError("Senha deve ter pelo menos 6 caracteres")

    # Perfil NotebookLM único baseado no hash do email
    profile_name = hashlib.sha256(email.encode()).hexdigest()[:12]

    with get_db() as conn:
        try:
            conn.execute(
                "INSERT INTO users (email, name, password_hash, notebooklm_profile) VALUES (?, ?, ?, ?)",
                (email, name.strip(), hash_password(password), profile_name),
            )
            conn.commit()
            user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
            return _row_to_dict(user)
        except sqlite3.IntegrityError:
            return None


def authenticate_user(email: str, password: str) -> dict | None:
    """Autentica usuário por email e senha. Retorna dict ou None."""
    email = email.strip().lower()
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and verify_password(password, user["password_hash"]):
            conn.execute(
                "UPDATE users SET last_login = datetime('now') WHERE id = ?",
                (user["id"],),
            )
            conn.commit()
            return _row_to_dict(user)
    return None


def get_user_by_id(user_id: int) -> dict | None:
    """Busca usuário por ID."""
    with get_db() as conn:
        user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return _row_to_dict(user) if user else None


def _row_to_dict(row) -> dict | None:
    """Converte sqlite3.Row para dict seguro (sem password_hash)."""
    if not row:
        return None
    d = dict(row)
    d.pop("password_hash", None)
    return d


# ===== JWT Tokens =====

def create_token(user_id: int, email: str) -> str:
    """Cria JWT token para o usuário."""
    if jwt is None:
        raise RuntimeError("PyJWT não instalado. pip install PyJWT")
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict | None:
    """Verifica e decodifica JWT token. Retorna payload ou None."""
    if jwt is None:
        return None
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


# ===== NotebookLM =====

def get_notebooklm_profile_path(profile_name: str) -> Path:
    """Retorna o caminho do perfil NotebookLM para o usuário."""
    return Path.home() / ".notebooklm" / "profiles" / (profile_name or "default")


def get_effective_notebooklm_profile(profile_name: str | None) -> str:
    """Retorna o perfil com credenciais ativas: se o específico existir usa ele, senão usa default se existir."""
    if profile_name:
        p_path = get_notebooklm_profile_path(profile_name) / "storage_state.json"
        if p_path.exists():
            return profile_name
    default_path = get_notebooklm_profile_path("default") / "storage_state.json"
    if default_path.exists():
        return "default"
    return profile_name or "default"


def check_notebooklm_auth(profile_name: str) -> bool:
    """Verifica se o perfil específico ou o default tem credenciais válidas."""
    effective = get_effective_notebooklm_profile(profile_name)
    storage = get_notebooklm_profile_path(effective) / "storage_state.json"
    return storage.exists()
