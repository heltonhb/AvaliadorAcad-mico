"""Testes para o módulo de auditoria bibliográfica e grounding (pipeline.bibliography)."""
import pytest
from pathlib import Path
from pipeline.bibliography import extract_dois_from_text, audit_bibliography


def test_extract_dois_from_text():
    sample_text = """
    Referências:
    [1] Silva, A. (2023). Machine Learning in Health. doi: 10.1016/j.jbi.2023.104321.
    [2] Santos, B. (2020). Deep Neural Networks. https://doi.org/10.1145/3377325.3377499
    [3] Repetição do mesmo: 10.1016/j.jbi.2023.104321
    """
    dois = extract_dois_from_text(sample_text)
    assert len(dois) == 2
    assert "10.1016/j.jbi.2023.104321" in dois
    assert "10.1145/3377325.3377499" in dois


def test_audit_bibliography_creates_artifacts(tmp_path):
    output_dir = tmp_path / "peer_review_test"
    output_dir.mkdir(parents=True)

    # Cria arquivo 03_sota_referencias.md simulado com DOIs
    md03 = output_dir / "03_sota_referencias.md"
    md03.write_text("""
    # SOTA e Referências
    - Vaswani et al. (2017). Attention is All You Need. DOI: 10.48550/arXiv.1706.03762
    - Devlin et al. (2018). BERT. DOI: 10.18653/v1/N19-1423
    """, encoding="utf-8")

    dummy_pdf = tmp_path / "paper.pdf"
    dummy_pdf.write_bytes(b"%PDF-1.4 dummy content")

    summary = audit_bibliography(str(dummy_pdf), output_dir, max_dois=2)

    assert "total_dois_found" in summary
    assert "recent_articles_pct" in summary

    # Verifica que os artefatos foram escritos no disco
    json_path = output_dir / "auditoria_bibliografica.json"
    md_path = output_dir / "08_auditoria_bibliografica.md"
    assert json_path.exists()
    assert md_path.exists()
    assert "# Auditoria Bibliográfica" in md_path.read_text(encoding="utf-8")
