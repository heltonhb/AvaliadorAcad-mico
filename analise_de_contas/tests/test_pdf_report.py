"""Testes para o gerador de parecer oficial em PDF (pipeline.pdf_report)."""
import pytest
from pathlib import Path
from pipeline.pdf_report import generate_official_pdf_report


def test_generate_official_pdf_report_success(tmp_path):
    output_dir = tmp_path / "peer_review_test"
    output_dir.mkdir(parents=True)

    # Cria módulo 06 sintese simulado com bloco estruturado
    md06 = output_dir / "06_sintese_parecer.md"
    md06.write_text("""
    # Parecer Final
    ## NOTA: 8.5
    ## DECISÃO FINAL: Minor Revisions
    
    ```json
    {
      "nota": 8.5,
      "decisao": "Minor Revisions",
      "coerencia_narrativa": 8.0,
      "pontos_fortes": ["Metodologia robusta", "Boa revisão teórica"],
      "fragilidades": ["Amostra pequena"],
      "recomendacoes_obrigatorias": ["Expandir o cálculo amostral"]
    }
    ```
    """, encoding="utf-8")

    ok = generate_official_pdf_report(output_dir, "teste_paper", domain="cs")
    assert ok is True

    pdf_file = output_dir / "parecer_banca_oficial.pdf"
    assert pdf_file.exists()
    assert pdf_file.stat().st_size > 1000  # PDF válido gerado
