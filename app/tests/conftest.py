"""Pytest configuration — ensures app is importable and pytest-asyncio is available."""
import sys
from pathlib import Path

# Add app directory to Python path
APP_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(APP_DIR))
