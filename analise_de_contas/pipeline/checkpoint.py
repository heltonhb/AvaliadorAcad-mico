"""Checkpoint e step status do pipeline."""
import json
from datetime import datetime
from pathlib import Path

from pipeline.constants import CHECKPOINT_FILE, STATUS_FILE


def load_checkpoint(output_dir):
    cp_path = Path(output_dir) / CHECKPOINT_FILE
    if cp_path.exists():
        try:
            return json.loads(cp_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return None
    return None


def save_checkpoint(output_dir, state):
    cp_path = Path(output_dir) / CHECKPOINT_FILE
    cp_path.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


def save_step(output_dir, step_id, label, status="running"):
    """Write current pipeline step to a JSON file for the API progress endpoint."""
    status_path = Path(output_dir) / STATUS_FILE
    data = {
        "step_id": step_id,
        "label": label,
        "status": status,
        "timestamp": datetime.now().isoformat(),
    }
    try:
        status_path.parent.mkdir(parents=True, exist_ok=True)
        status_path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    except Exception:
        pass
