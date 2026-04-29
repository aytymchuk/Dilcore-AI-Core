"""Tests for API endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test cases for health check endpoint."""

    def test_health_returns_200(self, test_client: TestClient) -> None:
        """Health endpoint should return 200 OK."""
        response = test_client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app_name" in data
        assert "model" in data


class TestScalarDocs:
    """Test cases for Scalar API documentation."""

    def test_scalar_endpoint_exists(self, test_client: TestClient) -> None:
        """Scalar docs endpoint should return HTML."""
        response = test_client.get("/scalar")

        assert response.status_code == 200

    def test_scalar_enables_json_spec_download(self, monkeypatch, test_client: TestClient) -> None:
        """Scalar docs should expose JSON/YAML OpenAPI downloads in the UI config."""
        from scalar_fastapi.scalar_fastapi import DocumentDownloadType

        captured: dict[str, object] = {}

        def _fake_get_scalar_api_reference(**kwargs):
            captured.update(kwargs)
            return "<html>ok</html>"

        # Patch where it's used (module import), not the library.
        monkeypatch.setattr("api.openapi.get_scalar_api_reference", _fake_get_scalar_api_reference)

        response = test_client.get("/scalar")
        assert response.status_code == 200
        assert captured.get("document_download_type") == DocumentDownloadType.BOTH

    def test_root_redirects_to_info(self, test_client: TestClient) -> None:
        """Root endpoint should provide docs info."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["docs"] == "/scalar"
