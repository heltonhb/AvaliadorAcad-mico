"""
Testes unitários para o pipeline de análise peer-review.
Roda: python3 -m pytest tests/test_pipeline.py -v
"""
import os
import re
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import pipeline as p
from pipeline.utils import run_cmd
from pipeline.checkpoint import load_checkpoint, save_checkpoint
from pipeline.lock import acquire_pipeline_lock, release_pipeline_lock
from pipeline.constants import CHECKPOINT_FILE
from utils import sanitize_filename
from artifacts import convert_to_csv


class TestRunCmd:
    def test_rejects_string(self):
        with pytest.raises(TypeError):
            run_cmd("echo hello")

    def test_runs_list(self):
        out, err, code = run_cmd(["echo", "hello"])
        assert code == 0

    def test_returns_error_code(self):
        _, _, code = run_cmd(["false"])
        assert code != 0

    def test_timeout(self):
        _, err, code = run_cmd(["sleep", "10"], timeout=1)
        assert code == 1


class TestConvertToCsv:
    def test_extracts_all_rows(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("""# Tabela de Erros

| Página | Linha | Tipo | Gravidade | Descrição |
|--------|-------|------|-----------|-----------|
| 1      | 5     | Gram | Grave     | Erro de concordância |
| 2      | 10    | Ref  | Moderado  | Citação incorreta |
| 3      | 15    | Gram | Leve      | Vírgula extra |
""", encoding="utf-8")
        csv = tmp_path / "out.csv"
        result = convert_to_csv(str(md), str(csv))
        assert result == 4  # header + 3 data rows
        assert csv.exists()
        content = csv.read_text(encoding="utf-8")
        assert "Página" in content
        assert "Linha" in content

    def test_no_table(self, tmp_path):
        md = tmp_path / "test.md"
        md.write_text("# Sem tabela\n\nApenas texto.", encoding="utf-8")
        csv = tmp_path / "out.csv"
        result = convert_to_csv(str(md), str(csv))
        assert result == 0


class TestCheckpoint:
    def test_save_and_load(self, tmp_path):
        state = {"notebook_id": "abc-123", "completed_modules": ["00", "01"]}
        save_checkpoint(tmp_path, state)
        loaded = load_checkpoint(tmp_path)
        assert loaded == state

    def test_no_checkpoint(self, tmp_path):
        assert load_checkpoint(tmp_path) is None

    def test_corrupted(self, tmp_path):
        (tmp_path / CHECKPOINT_FILE).write_text("NOT JSON {{{")
        assert load_checkpoint(tmp_path) is None



class TestSanitizeFilename:
    def test_path_traversal(self):
        assert sanitize_filename("../../../etc/passwd") == "passwd"

    def test_drops_special_chars(self):
        name = sanitize_filename("arquivo (1).pdf")
        assert re.match(r'^[\w\-]+$', name)

    def test_normal(self):
        assert sanitize_filename("artigo_2024.pdf") == "artigo_2024"

    def test_empty(self):
        assert sanitize_filename("") == "documento"


class TestArgparse:
    """Testa se o argparse rejeita argumentos inválidos."""

    @patch.object(sys, 'argv', ['pipeline.py'])
    def test_no_args_exits(self):
        with pytest.raises(SystemExit):
            p.main()

    @patch.object(sys, 'argv', ['pipeline.py', 'test.pdf', '--domain', 'invalid'])
    def test_bad_domain_exits(self):
        with pytest.raises(SystemExit):
            p.main()


class TestArtifactDownload:
    """Testa download_artifact e generate_artifact."""

    @patch("pipeline.notebooklm.run_cmd")
    def test_download_artifact_with_id(self, mock_run_cmd):
        from pipeline.notebooklm import download_artifact
        mock_run_cmd.return_value = ("", "", 0)
        ok = download_artifact("nb-123", "slide-deck", "aid-456", "/tmp/out.pdf")
        assert ok is True
        mock_run_cmd.assert_called_once()
        cmd = mock_run_cmd.call_args[0][0]
        assert cmd == ["notebooklm", "download", "slide-deck", "--notebook", "nb-123", "-a", "aid-456", "--force", "/tmp/out.pdf"]

    @patch("pipeline.notebooklm.run_cmd")
    def test_download_artifact_without_id(self, mock_run_cmd):
        from pipeline.notebooklm import download_artifact
        mock_run_cmd.return_value = ("", "", 0)
        ok = download_artifact("nb-123", "infographic", None, "/tmp/out.png")
        assert ok is True
        mock_run_cmd.assert_called_once()
        cmd = mock_run_cmd.call_args[0][0]
        assert cmd == ["notebooklm", "download", "infographic", "--notebook", "nb-123", "--force", "/tmp/out.png"]

