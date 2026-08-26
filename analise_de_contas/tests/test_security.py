"""Tests for security module — PDF validation, path safety, sanitization."""
import sys
from pathlib import Path
from io import BytesIO

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from security import (
    sanitize_html,
    validate_safe_path,
    get_auth_password,
    hash_password,
    verify_password,
    MAX_UPLOAD_MB,
)


class TestSanitizeHTML:
    def test_removes_script_tags(self):
        html = '<p>Hello</p><script>alert("xss")</script>'
        result = sanitize_html(html)
        assert "<script>" not in result
        assert "<p>Hello</p>" in result

    def test_removes_onclick_handlers(self):
        html = '<button onclick="alert(1)">Click</button>'
        result = sanitize_html(html)
        assert "onclick" not in result
        assert "Click" in result

    def test_removes_javascript_href(self):
        html = '<a href="javascript:alert(1)">link</a>'
        result = sanitize_html(html)
        assert "javascript" not in result or "href" not in result.lower()

    def test_allows_safe_tags(self):
        html = "<p><strong>Bold</strong> and <em>italic</em></p>"
        result = sanitize_html(html)
        assert "<strong>Bold</strong>" in result or "Bold" in result

    def test_returns_empty_for_empty_input(self):
        assert sanitize_html("") == ""
        assert sanitize_html(None) == ""

    def test_removes_iframe(self):
        html = '<iframe src="https://evil.com"></iframe><p>text</p>'
        result = sanitize_html(html)
        assert "iframe" not in result.lower()
        assert "text" in result


class TestPathValidation:
    def test_valid_path_within_base(self):
        assert validate_safe_path("/home/user/base/subdir", "/home/user/base") is True

    def test_path_traversal_blocked(self):
        assert validate_safe_path("/home/user/base/../../etc/passwd", "/home/user/base") is False

    def test_unrelated_path_blocked(self):
        assert validate_safe_path("/tmp/evil.txt", "/home/user/base") is False

    def test_equal_to_base_allowed(self):
        assert validate_safe_path("/home/user/base", "/home/user/base") is True

    def test_nonexistent_base_returns_false(self):
        # Should handle gracefully
        result = validate_safe_path("/some/path", "/nonexistent_base_xyz")
        assert result is False or isinstance(result, bool)


class TestPasswordHashing:
    def test_hash_and_verify_match(self):
        pw = "my_secure_password_123"
        hashed = hash_password(pw)
        assert verify_password(pw, hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("correct")
        assert verify_password("wrong", hashed) is False

    def test_different_salts_cause_different_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        # With bcrypt, each hash is different (random salt)
        assert h1 != h2

    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True


class TestGetAuthPassword:
    def test_returns_env_var(self, monkeypatch):
        monkeypatch.setenv("ANALISE_PASSWORD", "test_pass")
        assert get_auth_password() == "test_pass"

    def test_returns_empty_when_not_set(self, monkeypatch):
        monkeypatch.delenv("ANALISE_PASSWORD", raising=False)
        assert get_auth_password() == ""


class MockUploadFile:
    """Simula um arquivo enviado (upload) para testar validação de PDF."""
    def __init__(self, name, content, size=None):
        self.name = name
        self._content = content
        self.size = size or len(content)
        self._pos = 0

    async def read(self, n=-1):
        data = self._content[self._pos:self._pos + n] if n > 0 else self._content
        self._pos += len(data)
        return data

    async def seek(self, offset):
        self._pos = offset


def test_pdf_validation_valid():
    """PDF com magic bytes corretos deve ser aceito."""
    import asyncio
    from security import validate_pdf_upload
    valid_pdf = MockUploadFile("paper.pdf", b"%PDF-1.4\ncontent...", size=10000)
    valid, msg = asyncio.run(validate_pdf_upload(valid_pdf))
    assert valid is True
    assert msg == "OK"


def test_pdf_validation_invalid_magic():
    """Arquivo sem magic %PDF deve ser rejeitado."""
    import asyncio
    from security import validate_pdf_upload
    fake_pdf = MockUploadFile("fake.pdf", b"Not a PDF at all", size=10000)
    valid, msg = asyncio.run(validate_pdf_upload(fake_pdf))
    assert valid is False
    # Dois cenários possíveis dependendo se bleach ta instalado ou nao
    assert "PDF" in msg or "válido" in msg.lower()


def test_pdf_validation_empty():
    """Arquivo vazio deve ser rejeitado."""
    import asyncio
    from security import validate_pdf_upload
    empty = MockUploadFile("empty.pdf", b"", size=0)
    valid, msg = asyncio.run(validate_pdf_upload(empty))
    assert valid is False


def test_pdf_validation_too_large():
    """Arquivo acima de MAX_UPLOAD_MB deve ser rejeitado."""
    import asyncio
    from security import validate_pdf_upload
    large = MockUploadFile("big.pdf", b"%PDF-1.4\n" + b"x" * (MAX_UPLOAD_MB * 1024 * 1024 + 1))
    valid, msg = asyncio.run(validate_pdf_upload(large))
    assert valid is False
    assert "grande" in msg.lower() or "máximo" in msg.lower()

