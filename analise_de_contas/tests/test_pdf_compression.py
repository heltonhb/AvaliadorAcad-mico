"""Testes para compressão e otimização de PDFs com Ghostscript."""
import pytest
from pathlib import Path
from pipeline.utils import compress_pdf_ghostscript, compress_pdf_if_large


def test_compress_pdf_if_large_under_threshold(tmp_path):
    # Cria um PDF pequeno
    small_pdf = tmp_path / "paper_small.pdf"
    small_pdf.write_bytes(b"%PDF-1.4 " + b"x" * 1024)

    out_path, compressed = compress_pdf_if_large(str(small_pdf), tmp_path, threshold_mb=100.0)
    assert compressed is False
    assert out_path == str(small_pdf)


def test_compress_pdf_if_large_missing_file(tmp_path):
    missing_pdf = tmp_path / "non_existent.pdf"
    out_path, compressed = compress_pdf_if_large(str(missing_pdf), tmp_path, threshold_mb=10.0)
    assert compressed is False
    assert out_path == str(missing_pdf)


def test_compress_pdf_ghostscript_valid(tmp_path):
    input_pdf = tmp_path / "sample.pdf"
    output_pdf = tmp_path / "sample_out.pdf"
    # Simple minimal valid PDF structure
    input_pdf.write_bytes(
        b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
        b"xref\n0 4\n0000000000 65535 f \n0000000010 00000 n \n0000000060 00000 n \n0000000117 00000 n \n"
        b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n186\n%%EOF"
    )
    result = compress_pdf_ghostscript(str(input_pdf), str(output_pdf))
    assert result is True
    assert output_pdf.exists()
    assert output_pdf.stat().st_size > 0

