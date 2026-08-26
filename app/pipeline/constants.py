"""Constantes do pipeline."""
from pathlib import Path
import os

APP_DIR = Path(__file__).resolve().parent.parent
BASE_DIR = Path(os.environ.get("ANALISE_BASE_DIR", APP_DIR.parent))

CHECKPOINT_FILE = ".checkpoint.json"
STATUS_FILE = "pipeline_status.json"
