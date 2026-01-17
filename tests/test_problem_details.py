"""Tests for Problem Details error handling.

This module tests the RFC 7807 Problem Details error responses
from the API endpoints.
"""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from ai_agent.main import app

client = TestClient(app, raise_server_exceptions=False)


class TestProblemDetailsResponses:
    """Test Problem Details error responses."""

    def test_health_endpoint_success(self) -> None:
        """Test that health endpoint returns success."""
        response = client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == "healthy"
        assert data["version"] == "0.1.0"

    def test_validation_error_empty_prompt(self) -> None:
        """Test validation error for empty prompt."""
        response = client.post(
            "/api/v1/generate",
            json={"prompt": ""},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.headers["content-type"] == "application/problem+json"

        data = response.json()
        assert data["type"] == "https://api.dilcore.ai/errors/validation-error"
        assert data["title"] == "Validation Error"
        assert data["status"] == 422
        assert "validation" in data["detail"].lower()
        assert data["instance"] == "/api/v1/generate"
        assert "errors" in data
        assert "prompt" in data["errors"]

    def test_validation_error_prompt_too_long(self) -> None:
        """Test validation error for prompt that's too long."""
        response = client.post(
            "/api/v1/generate",
            json={"prompt": "x" * 5000},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.headers["content-type"] == "application/problem+json"

        data = response.json()
        assert data["type"] == "https://api.dilcore.ai/errors/validation-error"
        assert data["title"] == "Validation Error"
        assert data["status"] == 422
        assert "errors" in data

    def test_validation_error_missing_prompt(self) -> None:
        """Test validation error for missing prompt field."""
        response = client.post(
            "/api/v1/generate",
            json={},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.headers["content-type"] == "application/problem+json"

        data = response.json()
        assert data["type"] == "https://api.dilcore.ai/errors/validation-error"
        assert data["status"] == 422
        assert "errors" in data

    def test_custom_validation_error(self) -> None:
        """Test custom validation error from business logic."""
        response = client.post(
            "/api/v1/generate",
            json={"prompt": "test validation error"},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.headers["content-type"] == "application/problem+json"

        data = response.json()
        assert data["type"] == "https://api.dilcore.ai/errors/validation-error"
        assert data["title"] == "Validation Error"
        assert data["status"] == 422
        assert "invalid prompt content" in data["detail"].lower()
        assert data["instance"] == "/api/v1/generate"
        assert "errors" in data
        assert "prompt" in data["errors"]

    def test_llm_api_error(self) -> None:
        """Test LLM API error."""
        response = client.post(
            "/api/v1/generate",
            json={"prompt": "test llm error"},
        )
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert response.headers["content-type"] == "application/problem+json"

        data = response.json()
        assert data["type"] == "https://api.dilcore.ai/errors/llm-api"
        assert data["title"] == "LLM API"
        assert data["status"] == 502
        assert "llm api" in data["detail"].lower()
        assert data["instance"] == "/api/v1/generate"
        assert "errors" in data

    def test_parsing_error(self) -> None:
        """Test parsing error."""
        response = client.post(
            "/api/v1/generate",
            json={"prompt": "test parsing error"},
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.headers["content-type"] == "application/problem+json"

        data = response.json()
        assert data["type"] == "https://api.dilcore.ai/errors/parsing"
        assert data["title"] == "Parsing"
        assert data["status"] == 500
        assert "parse" in data["detail"].lower()
        assert data["instance"] == "/api/v1/generate"
        assert "errors" in data

    def test_template_generation_error(self) -> None:
        """Test template generation error."""
        response = client.post(
            "/api/v1/generate",
            json={"prompt": "test template error"},
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.headers["content-type"] == "application/problem+json"

        data = response.json()
        assert data["type"] == "https://api.dilcore.ai/errors/template-generation"
        assert data["title"] == "Template Generation"
        assert data["status"] == 500
        assert "template generation" in data["detail"].lower()
        assert data["instance"] == "/api/v1/generate"
        assert "errors" in data

    def test_http_exception_error(self) -> None:
        """Test HTTP exception error."""
        response = client.post(
            "/api/v1/generate",
            json={"prompt": "test http error"},
        )
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.headers["content-type"] == "application/problem+json"

        data = response.json()
        assert data["type"] == "https://api.dilcore.ai/errors/service-unavailable"
        assert data["title"] == "Service Unavailable"
        assert data["status"] == 503
        assert "unavailable" in data["detail"].lower()
        assert data["instance"] == "/api/v1/generate"

    def test_unhandled_exception_error(self) -> None:
        """Test unhandled exception error."""
        response = client.post(
            "/api/v1/generate",
            json={"prompt": "test unhandled error"},
        )
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.headers["content-type"] == "application/problem+json"

        data = response.json()
        assert data["type"] == "https://api.dilcore.ai/errors/internal-server-error"
        assert data["title"] == "Internal Server Error"
        assert data["status"] == 500
        assert "unexpected error" in data["detail"].lower()
        assert data["instance"] == "/api/v1/generate"
        # Unhandled exceptions should not expose internal details
        assert "errors" not in data or data["errors"] is None

    def test_successful_generation(self) -> None:
        """Test successful template generation."""
        response = client.post(
            "/api/v1/generate",
            json={"prompt": "test successful generation"},
        )
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "template" in data
        assert "metadata" in data
        assert "test successful generation" in data["template"]

    def test_error_endpoint_validation(self) -> None:
        """Test error endpoint with validation error."""
        response = client.get("/api/v1/error/validation")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.headers["content-type"] == "application/problem+json"

        data = response.json()
        assert data["type"] == "https://api.dilcore.ai/errors/validation-error"
        assert data["status"] == 422

    def test_error_endpoint_llm(self) -> None:
        """Test error endpoint with LLM error."""
        response = client.get("/api/v1/error/llm")
        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert response.headers["content-type"] == "application/problem+json"

        data = response.json()
        assert data["type"] == "https://api.dilcore.ai/errors/llm-api"
        assert data["status"] == 502

    def test_error_endpoint_parsing(self) -> None:
        """Test error endpoint with parsing error."""
        response = client.get("/api/v1/error/parsing")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.headers["content-type"] == "application/problem+json"

        data = response.json()
        assert data["type"] == "https://api.dilcore.ai/errors/parsing"
        assert data["status"] == 500

    def test_error_endpoint_template(self) -> None:
        """Test error endpoint with template error."""
        response = client.get("/api/v1/error/template")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.headers["content-type"] == "application/problem+json"

        data = response.json()
        assert data["type"] == "https://api.dilcore.ai/errors/template-generation"
        assert data["status"] == 500

    def test_error_endpoint_http(self) -> None:
        """Test error endpoint with HTTP error."""
        response = client.get("/api/v1/error/http")
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.headers["content-type"] == "application/problem+json"

        data = response.json()
        assert data["type"] == "https://api.dilcore.ai/errors/not-found"
        assert data["status"] == 404

    def test_error_endpoint_unhandled(self) -> None:
        """Test error endpoint with unhandled error."""
        response = client.get("/api/v1/error/unhandled")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.headers["content-type"] == "application/problem+json"

        data = response.json()
        assert data["type"] == "https://api.dilcore.ai/errors/internal-server-error"
        assert data["status"] == 500

    def test_problem_details_structure(self) -> None:
        """Test that problem details have correct structure."""
        response = client.get("/api/v1/error/validation")
        data = response.json()

        # Required fields
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "instance" in data

        # Type should be a URL
        assert data["type"].startswith("https://")
        assert "/errors/" in data["type"]

        # Status should match HTTP status code
        assert data["status"] == response.status_code

        # Instance should be the request path
        assert data["instance"] == "/api/v1/error/validation"

    def test_root_endpoint(self) -> None:
        """Test root endpoint returns welcome message."""
        response = client.get("/")
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "message" in data
        assert "docs" in data
        assert "version" in data
