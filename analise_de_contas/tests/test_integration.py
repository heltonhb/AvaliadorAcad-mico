"""
Testes de integração para o pipeline de análise peer-review.
Testa o fluxo completo: preparar dados → executar pipeline → verificar arquivos gerados.
Roda: python3 -m pytest tests/test_integration.py -v
"""
import os
import sys
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import sanitize_filename, find_all_peer_review_dirs, format_file_size, file_icon
from artifacts import convert_to_csv, generate_pptx_fallback, generate_mira_artifact
from security import validate_pdf_upload, sanitize_html, validate_safe_path


# ===== Fixture: diretório temporário com dados simulados =====

@pytest.fixture
def sample_output_dir():
    """Cria diretório temporário com arquivos simulados de uma análise."""
    tmpdir = Path(tempfile.mkdtemp())

    # Simular relatórios Markdown
    (tmpdir / "00_estrutura_documento.md").write_text(
        "# Estrutura do Documento\n\n## 1. Introdução\nObjetivo do estudo.\n\n## 2. Metodologia\nDesenho experimental.\n",
        encoding="utf-8",
    )
    (tmpdir / "01_metodologia.md").write_text(
        "# Auditoria Metodológica\n\n1. Desenho: Estudo observacional.\n2. Amostra: n=200.\n",
        encoding="utf-8",
    )
    (tmpdir / "04_gaps_logicos.md").write_text(
        "# Gaps Lógicos\n\n1. Falta de grupo controle.\n2. Amostra não representativa.\n3. Viés de seleção.\n",
        encoding="utf-8",
    )
    (tmpdir / "05_analise_escrita.md").write_text(
        "# Análise de Escrita\n\n| # | Página | Tipo | Gravidade | Fonte | Trecho | Correção | Página | Linha | Gravidade |\n"
        "|---|--------|------|-----------|-------|--------|----------|--------|-------|----------|\n"
        "| 1 | 5 | Ortográfico | Alta | L10 | O estudo foi realizado com intenção | O estudo foi realizado com intenção | 5 | L10 | ALTA |\n"
        "| 2 | 8 | Gramatical | Média | L20 | Os dados demonstram que os resultado | Os dados demonstram que os resultados | 8 | L20 | MÉDIA |\n",
        encoding="utf-8",
    )
    (tmpdir / "06_sintese_parecer.md").write_text(
        "# Parecer Final\n\n## Resumo Executivo\nO estudo apresenta lacunas metodológicas.\n\n## Veredito\nArtigo requer revisões substanciais.\n\n## Pontos Fortes\n1. Tema relevante\n2. Boa revisão bibliográfica\n\n## Fragilidades Principais\n1. Amostra pequena\n2. Falta grupo controle\n\n## Carta ao Editor\nRecomendo revisão majoritária.\n\n## DECISÃO FINAL: Major Revisions\n## NOTA: 6.5\n",
        encoding="utf-8",
    )

    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


# ===== Testes de Integração: Conversão CSV =====

class TestCsvIntegration:
    def test_csv_from_realistic_md(self, sample_output_dir):
        """Testa conversão CSV a partir de relatório Markdown realista."""
        md_file = str(sample_output_dir / "05_analise_escrita.md")
        csv_file = str(sample_output_dir / "tabela_erros.csv")

        n = convert_to_csv(md_file, csv_file)
        assert n >= 2  # Pelo menos header + 2 linhas

        import csv
        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            rows = list(reader)
            assert len(rows) >= 3
            # Verificar que contém dados de erros
            content = open(csv_file, encoding="utf-8").read()
            assert "Ortográfico" in content or "Gramatical" in content


# ===== Testes de Integração: PPTX Fallback =====

class TestPptxIntegration:
    def test_pptx_completa_with_real_data(self, sample_output_dir):
        """Testa geração PPTX completa com dados realistas."""
        result = generate_pptx_fallback(sample_output_dir, "paper_teste", "completa")
        assert result is True

        pptx_file = sample_output_dir / "apresentacao_completa.pptx"
        assert pptx_file.exists()
        assert pptx_file.stat().st_size > 5000  # PPTX real deve ser > 5KB

    def test_pptx_auditoria_with_real_data(self, sample_output_dir):
        """Testa geração PPTX de auditoria com dados realistas."""
        result = generate_pptx_fallback(sample_output_dir, "paper_teste", "auditoria")
        assert result is True

        pptx_file = sample_output_dir / "apresentacao_auditoria.pptx"
        assert pptx_file.exists()


# ===== Testes de Integração: HTML Animado =====

class TestMiraIntegration:
    def test_mira_html_generation(self, sample_output_dir):
        """Testa geração da apresentação animada HTML."""
        result = generate_mira_artifact(sample_output_dir, "paper_teste")
        assert result is True

        html_file = sample_output_dir / "apresentacao_animada.html"
        assert html_file.exists()
        assert html_file.stat().st_size > 2000

        content = html_file.read_text(encoding="utf-8")
        assert "Peer-Review" in content
        assert "paper_teste" in content
        assert "6.5" in content  # NOTA from parecer
        assert "Major Revisions" in content  # Decisão from parecer

    def test_mira_html_no_data(self):
        """Testa geração HTML com diretório vazio."""
        with tempfile.TemporaryDirectory() as td:
            result = generate_mira_artifact(Path(td), "empty_paper")
            assert result is True
            html_file = Path(td) / "apresentacao_animada.html"
            assert html_file.exists()


# ===== Testes de Integração: Fluxo Completo do Pipeline =====

class TestPipelineFlow:
    def test_full_flow_with_mock_notebooklm(self, sample_output_dir):
        """Testa o fluxo completo do pipeline com mocks do NotebookLM."""
        import pipeline as p
        import pipeline.runner as runner

        # Mock todas as chamadas externas — devem ser patcheadas no módulo
        # runner onde são importadas (não no __init__ nem no notebooklm)
        with patch.object(runner, "create_notebook", return_value="mock-nb-id"), \
             patch.object(runner, "configure_notebook", return_value=(True, "")), \
             patch.object(runner, "check_ocr_needed", return_value=False), \
             patch.object(runner, "add_source", return_value=True), \
             patch.object(runner, "wait_source", return_value=True), \
             patch.object(runner, "run_ask", return_value=True), \
             patch.object(runner, "generate_artifact", return_value=(None, False)), \
             patch.object(runner, "download_artifact", return_value=True), \
             patch.object(runner, "generate_pptx_fallback", return_value=True), \
             patch.object(runner, "generate_mira_artifact", return_value=True):

            # Criar PDF falso
            pdf_path = sample_output_dir / "test_paper.pdf"
            pdf_path.write_bytes(b"%PDF-1.4 fake pdf content")

            # Executar pipeline — com mocks deve completar sem erro
            with patch("sys.argv", [
                "pipeline.py", str(pdf_path),
                "--domain", "cs",
                "--mode", "lite",
                "--output-dir", str(sample_output_dir),
                "--force",
            ]):
                try:
                    runner.main()
                except SystemExit as e:
                    pytest.fail(f"Pipeline levantou SystemExit({e.code}) com mocks")

            # Verificar artefatos gerados (dentro de peer_review_*/)
            out_subdirs = list(sample_output_dir.glob("peer_review_*"))
            assert len(out_subdirs) == 1, f"Subdir peer_review_* não encontrado: {list(sample_output_dir.iterdir())}"
            out_dir = out_subdirs[0]
            assert (out_dir / "relatorio_completo.md").exists()
            assert (out_dir / ".checkpoint.json").exists()
            checkpoint = json.loads((out_dir / ".checkpoint.json").read_text(encoding="utf-8"))
            assert checkpoint["notebook_id"] == "mock-nb-id"
            assert checkpoint["artifacts_done"] is True
            assert len(checkpoint["completed_modules"]) == 6  # modo lite pula 03 e 07

    def test_checkpoint_resume_flow(self, sample_output_dir):
        """Testa que o checkpoint permite retomar de onde parou."""
        import pipeline as p

        # Criar checkpoint parcial
        state = {
            "notebook_id": "existing-nb-id",
            "source_added": True,
            "source_ready": True,
            "completed_modules": ["00", "01", "04"],
            "artifacts_done": False,
        }
        p.save_checkpoint(sample_output_dir, state)

        # Carregar e verificar
        loaded = p.load_checkpoint(sample_output_dir)
        assert loaded["notebook_id"] == "existing-nb-id"
        assert "00" in loaded["completed_modules"]
        assert "01" in loaded["completed_modules"]
        assert "04" in loaded["completed_modules"]
        assert len(loaded["completed_modules"]) == 3


# ===== Testes de Integração: find_all_peer_review_dirs =====

class TestFindDirsIntegration:
    def test_finds_peer_review_dirs(self):
        """Testa busca de diretórios peer_review em múltiplos locais."""
        with tempfile.TemporaryDirectory() as base:
            base_path = Path(base)

            # Criar estrutura "Arquivos das bancas"
            bancas = base_path / "Arquivos das bancas"
            bancas.mkdir(parents=True)
            (bancas / "peer_review_paper1").mkdir()
            (bancas / "peer_review_paper2").mkdir()
            (bancas / "other_dir").mkdir()  # Não deve aparecer

            # Criar estrutura "analises" (legacy)
            analises = base_path / "analises"
            analises.mkdir()
            (analises / "peer_review_legacy").mkdir()

            dirs = find_all_peer_review_dirs(base_path)
            names = [d.name for d in dirs]
            assert len(dirs) == 3
            assert "peer_review_paper1" in names
            assert "peer_review_paper2" in names
            assert "peer_review_legacy" in names
            assert "other_dir" not in names


# ===== Testes de Integração: Segurança =====

class TestSecurityIntegration:
    def test_sanitize_html_complex_payload(self):
        """Testa sanitização HTML com payload complexo."""
        payload = '''
        <div>
            <p>Texto normal</p>
            <script>alert('XSS')</script>
            <img src=x onerror="alert(1)">
            <iframe src="evil.com"></iframe>
            <a href="javascript:alert('xss')">click</a>
            <style>body{background:red}</style>
        </div>
        '''
        result = sanitize_html(payload)
        assert "<script>" not in result
        assert "<iframe>" not in result
        assert "javascript:" not in result
        assert "Texto normal" in result

    def test_validate_pdf_upload_realistic(self):
        """Testa validação de upload com dados realistas."""
        import asyncio

        class FakeUpload:
            def __init__(self, content, size):
                self._content = content
                self._pos = 0
                self.size = size

            async def read(self, n=-1):
                data = self._content[self._pos:self._pos + n] if n > 0 else self._content[self._pos:]
                self._pos += len(data)
                return data

            async def seek(self, pos):
                self._pos = pos

        # PDF válido
        valid = FakeUpload(b"%PDF-1.4 valid content", 1024)
        ok, msg = asyncio.run(validate_pdf_upload(valid))
        assert ok is True

        # PDF muito grande (> MAX_UPLOAD_MB)
        big = FakeUpload(b"%PDF-1.4", 600 * 1024 * 1024)  # 600MB (> 500MB)
        ok, msg = asyncio.run(validate_pdf_upload(big))
        assert ok is False
        assert "grande" in msg

        # Não PDF
        fake = FakeUpload(b"<html>not a pdf</html>", 100)
        ok, msg = asyncio.run(validate_pdf_upload(fake))
        assert ok is False
        assert "inválido" in msg

        # None
        ok, msg = asyncio.run(validate_pdf_upload(None))
        assert ok is False

