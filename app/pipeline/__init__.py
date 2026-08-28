"""Pipeline de Análise Científica — módulos especializados.

Re-exporta funções principais para compatibilidade (import pipeline as p).
Usa __getattr__ para runner (evita circular import quando executado via -m).
"""
from pipeline.utils import run_cmd, check_ocr_needed
from pipeline.checkpoint import load_checkpoint, save_checkpoint, save_step
from pipeline.lock import acquire_pipeline_lock, release_pipeline_lock
from pipeline.constants import APP_DIR, BASE_DIR, CHECKPOINT_FILE, STATUS_FILE
from pipeline.notebooklm import (
    create_notebook,
    configure_notebook,
    add_source,
    wait_source,
    run_ask,
    generate_artifact,
    download_artifact,
)
from artifacts import convert_to_csv, generate_mira_artifact


def __getattr__(name):
    """Lazy import de pipeline.runner para evitar circular import com '-m pipeline.runner'."""
    if name in ("main", "_run_pipeline", "log"):
        import pipeline.runner as runner
        return getattr(runner, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
