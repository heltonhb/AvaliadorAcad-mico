"""Tests for the backend API — health, auth, config, endpoints."""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import app
from auth import create_user, create_token, authenticate_user, _ensure_db


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """Ensure database is initialized before tests."""
    _ensure_db()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def auth_token():
    """Create a test user and return auth token."""
    # Create user via direct DB call
    user = create_user("test@example.com", "testpass123", "Test User")
    if not user:
        # User might already exist
        user = authenticate_user("test@example.com", "testpass123")
    assert user is not None, "Failed to create/authenticate test user"
    token = create_token(user["id"], user["email"])
    return token


class TestHealth:
    def test_health_returns_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_health_live(self, client):
        r = client.get("/api/health/live")
        assert r.status_code == 200
        assert r.json()["status"] == "alive"

    def test_health_ready(self, client):
        r = client.get("/api/health/ready")
        # Ready may be degraded in test env (notebooklm not installed)
        assert r.status_code in (200, 503)
        data = r.json()
        assert "checks" in data
        assert "database" in data["checks"]

    def test_health_public_no_auth(self, client):
        """Health endpoint should not require auth."""
        r = client.get("/api/health")
        assert r.status_code == 200


class TestConfig:
    def test_config_returns_options(self, client):
        r = client.get("/api/config")
        assert r.status_code == 200
        data = r.json()
        assert "domains" in data
        assert "cs" in data["domains"]
        assert "max_upload_mb" in data
        assert "default_mode" in data

    def test_config_has_domains(self, client):
        r = client.get("/api/config")
        assert r.status_code == 200
        data = r.json()
        assert "domains" in data
        assert isinstance(data["domains"], dict)
        assert len(data["domains"]) >= 3

    def test_config_public_no_auth(self, client):
        r = client.get("/api/config")
        assert r.status_code == 200


class TestAuthMiddleware:
    def test_protected_endpoints_require_auth(self, client):
        """Protected endpoints require authentication."""
        r = client.get("/api/analyses")
        # Should get 401 without auth
        assert r.status_code == 401

    def test_public_routes_exempt(self, client):
        """Public routes should not require auth."""
        for path in ["/api/health", "/api/health/live", "/api/config"]:
            r = client.get(path)
            assert r.status_code == 200, f"Path {path} should be public"
        # /api/health/ready may return 503 if notebooklm not available
        r = client.get("/api/health/ready")
        assert r.status_code in (200, 503)


class TestPipelineEndpoints:
    def test_pipeline_status_returns_idle(self, client, auth_token):
        r = client.get("/api/pipeline/status", headers={"Authorization": f"Bearer {auth_token}"})
        assert r.status_code == 200
        data = r.json()
        assert data["running"] is False

    def test_pipeline_progress_returns_idle(self, client, auth_token):
        r = client.get("/api/pipeline/progress", headers={"Authorization": f"Bearer {auth_token}"})
        assert r.status_code == 200
        data = r.json()
        assert data["running"] is False

    def test_start_without_pdf_returns_404(self, client, auth_token):
        r = client.post(
            "/api/pipeline/start",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={"file_path": "/nonexistent.pdf", "domain": "cs", "mode": "full"},
        )
        assert r.status_code == 404


class TestAnalysesEndpoint:
    def test_list_analyses_returns_list(self, client, auth_token):
        r = client.get("/api/analyses", headers={"Authorization": f"Bearer {auth_token}"})
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_nonexistent_analysis_returns_404(self, client, auth_token):
        r = client.get("/api/analyses/nonexistent_id", headers={"Authorization": f"Bearer {auth_token}"})
        assert r.status_code == 404


class TestUploadEndpoint:
    def test_upload_requires_auth(self, client):
        r = client.post("/api/upload", files={"file": ("test.pdf", b"%PDF-1.4 test", "application/pdf")})
        assert r.status_code == 401

    def test_upload_valid_pdf(self, client, auth_token):
        # Create a minimal valid PDF
        pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\nxref\n0 4\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \ntrailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n193\n%%EOF"
        files = {"file": ("test.pdf", pdf_content, "application/pdf")}
        r = client.post("/api/upload", headers={"Authorization": f"Bearer {auth_token}"}, files=files)
        assert r.status_code == 200
        data = r.json()
        assert "path" in data
        assert "safe_name" in data

    def test_upload_invalid_file_rejected(self, client, auth_token):
        files = {"file": ("test.txt", b"not a pdf", "text/plain")}
        r = client.post("/api/upload", headers={"Authorization": f"Bearer {auth_token}"}, files=files)
        assert r.status_code == 400
        data = r.json()
        assert "detail" in data