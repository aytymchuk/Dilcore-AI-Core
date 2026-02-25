"""Tests for API endpoints."""

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

    def test_root_redirects_to_info(self, test_client: TestClient) -> None:
        """Root endpoint should provide docs info."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["docs"] == "/scalar"
