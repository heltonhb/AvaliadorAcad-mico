"""Tests for the backend API — health, auth, config, endpoints."""
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Ensure app is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from api import app, _API_KEY


@pytest.fixture
def client():
    return TestClient(app)


class TestHealth:
    def test_health_returns_ok(self, client):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert "version" in data
        assert "pipeline_script" in data

    def test_health_public_no_auth(self, client):
        """Health endpoint should not require API key."""
        r = client.get("/api/health")
        assert r.status_code == 200


class TestConfig:
    def test_config_returns_options(self, client):
        r = client.get("/api/config")
        assert r.status_code == 200
        data = r.json()
        assert "domains" in data
        assert "modes" in data
        assert "max_upload_mb" in data
        assert data["max_upload_mb"] >= 100
        assert "compress_threshold_mb" in data
        assert "requires_auth" in data

    def test_config_has_domains(self, client):
        r = client.get("/api/config")
        data = r.json()
        assert "cs" in data["domains"]
        assert "med" in data["domains"]
        assert "human" in data["domains"]

    def test_config_public_no_auth(self, client):
        r = client.get("/api/config")
        assert r.status_code == 200


class TestAuthMiddleware:
    def test_auth_disabled_when_no_key(self, client):
        """If ANALISE_PASSWORD is not set, all endpoints are open."""
        # _API_KEY is '' when no env var set
        r = client.get("/api/analyses")
        assert r.status_code == 200  # Not 401

    def test_auth_enabled_blocks_without_key(self, monkeypatch, client):
        monkeypatch.setattr("api._API_KEY", "secret123")
        r = client.get("/api/analyses")
        assert r.status_code == 401
        assert "API Key" in r.json()["detail"]

    def test_auth_enabled_blocks_wrong_key(self, monkeypatch, client):
        monkeypatch.setattr("api._API_KEY", "secret123")
        r = client.get("/api/analyses", headers={"X-API-Key": "wrong-key"})
        assert r.status_code == 401

    def test_auth_enabled_allows_correct_key(self, monkeypatch, client):
        monkeypatch.setattr("api._API_KEY", "secret123")
        r = client.get("/api/analyses", headers={"X-API-Key": "secret123"})
        assert r.status_code == 200  # Not 401

    def test_auth_public_routes_exempt(self, monkeypatch, client):
        """Health and config should work even with auth enabled."""
        monkeypatch.setattr("api._API_KEY", "secret123")
        r = client.get("/api/health")
        assert r.status_code == 200
        r = client.get("/api/config")
        assert r.status_code == 200


class TestPipelineEndpoints:
    def test_pipeline_status_returns_idle(self, client):
        r = client.get("/api/pipeline/status")
        assert r.status_code == 200
        data = r.json()
        assert "running" in data

    def test_pipeline_progress_returns_idle(self, client):
        r = client.get("/api/pipeline/progress")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "idle"
        assert data["running"] is False

    def test_start_without_pdf_returns_404(self, client):
        r = client.post(
            "/api/pipeline/start",
            json={"file_path": "/nonexistent/paper.pdf"},
        )
        assert r.status_code == 404


class TestAnalysesEndpoint:
    def test_list_analyses_returns_list(self, client):
        r = client.get("/api/analyses")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_nonexistent_analysis_returns_404(self, client):
        r = client.get("/api/analyses/nonexistent_id")
        assert r.status_code == 404


class TestUploadEndpoint:
    def test_upload_valid_pdf(self, client):
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        files = {"file": ("sample.pdf", pdf_content, "application/pdf")}
        r = client.post("/api/upload", files=files)
        assert r.status_code == 200
        data = r.json()
        assert data["filename"] == "sample.pdf"
        assert "path" in data
        assert data["size"] == len(pdf_content)
        assert data["was_compressed"] is False

    def test_upload_invalid_file_rejected(self, client):
        files = {"file": ("test.txt", b"not a pdf", "text/plain")}
        r = client.post("/api/upload", files=files)
        assert r.status_code == 400

