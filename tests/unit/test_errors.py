"""Tests for Problem Details error handling."""

import pytest
from fastapi import status
from pydantic import ValidationError as PydanticValidationError

from api.schemas.errors import ProblemDetails
from shared.exceptions import (
    AIAgentException,
    ConfigurationError,
    LLMProviderError,
    ResourceNotFoundError,
    ValidationError,
)


class TestProblemDetailsSchema:
    """Test cases for ProblemDetails schema."""

    def test_problem_details_schema_valid(self) -> None:
        """ProblemDetails should validate with correct fields."""
        problem = ProblemDetails(
            type="https://api.dilcore.ai/problems/validation-error",
            title="Validation Error",
            status=400,
            detail="Invalid request data",
            instance="/api/v1/metadata/generate",
        )

        assert problem.type == "https://api.dilcore.ai/problems/validation-error"
        assert problem.title == "Validation Error"
        assert problem.status == 400
        assert problem.detail == "Invalid request data"
        assert problem.instance == "/api/v1/metadata/generate"

    def test_problem_details_rejects_non_error_status(self) -> None:
        """ProblemDetails should reject status codes outside 400-599 range."""
        with pytest.raises(PydanticValidationError, match="greater than or equal to 400"):
            ProblemDetails(
                type="https://api.dilcore.ai/problems/test",
                title="Test",
                status=200,
                detail="Test detail",
                instance="/test",
            )

    def test_problem_details_accepts_4xx_status(self) -> None:
        """ProblemDetails should accept 4xx status codes."""
        problem = ProblemDetails(
            type="https://api.dilcore.ai/problems/not-found",
            title="Not Found",
            status=404,
            detail="Resource not found",
            instance="/api/v1/test",
        )
        assert problem.status == 404

    def test_problem_details_accepts_5xx_status(self) -> None:
        """ProblemDetails should accept 5xx status codes."""
        problem = ProblemDetails(
            type="https://api.dilcore.ai/problems/internal-error",
            title="Internal Server Error",
            status=500,
            detail="An error occurred",
            instance="/api/v1/test",
        )
        assert problem.status == 500

    def test_problem_details_serialization(self) -> None:
        """ProblemDetails should serialize to JSON correctly."""
        problem = ProblemDetails(
            type="https://api.dilcore.ai/problems/test",
            title="Test Error",
            status=400,
            detail="Test detail",
            instance="/test",
        )

        json_data = problem.model_dump()

        assert json_data["type"] == "https://api.dilcore.ai/problems/test"
        assert json_data["title"] == "Test Error"
        assert json_data["status"] == 400
        assert json_data["detail"] == "Test detail"
        assert json_data["instance"] == "/test"


class TestCustomExceptions:
    """Test cases for custom exception classes."""

    def test_validation_error_defaults(self) -> None:
        """ValidationError should have correct defaults."""
        exc = ValidationError("Invalid input")

        assert exc.message == "Invalid input"
        assert exc.problem_type == "validation-error"
        assert exc.title == "Validation Error"
        assert exc.status_code == 400

    def test_llm_provider_error_defaults(self) -> None:
        """LLMProviderError should have correct defaults."""
        exc = LLMProviderError()

        assert exc.message == "LLM provider communication failed"
        assert exc.problem_type == "llm-provider-error"
        assert exc.title == "LLM Provider Error"
        assert exc.status_code == 502

    def test_configuration_error_defaults(self) -> None:
        """ConfigurationError should have correct defaults."""
        exc = ConfigurationError("Missing API key")

        assert exc.message == "Missing API key"
        assert exc.problem_type == "configuration-error"
        assert exc.title == "Configuration Error"
        assert exc.status_code == 500

    def test_resource_not_found_error_defaults(self) -> None:
        """ResourceNotFoundError should have correct defaults."""
        exc = ResourceNotFoundError("Missing X")

        assert exc.message == "Missing X"
        assert exc.problem_type == "not-found"
        assert exc.title == "Not Found"
        assert exc.status_code == 404

    def test_base_exception_inheritance(self) -> None:
        """All custom exceptions should inherit from AIAgentException."""
        assert isinstance(ValidationError("test"), AIAgentException)
        assert isinstance(LLMProviderError(), AIAgentException)
        assert isinstance(ConfigurationError("test"), AIAgentException)
        assert isinstance(ResourceNotFoundError("test"), AIAgentException)


class TestGlobalExceptionHandlers:
    """Test cases for global exception handlers."""

    AUTH0_TEST_ENV = {
        "AUTH0__DOMAIN": "test.auth0.com",
        "AUTH0__CLIENT_ID": "test-id",
        "AUTH0__CLIENT_SECRET": "test-secret",
        "AUTH0__AUDIENCE": "test-audience",
    }

    def test_validation_error_returns_problem_details(self, authenticated_client) -> None:
        """Validation errors should return Problem Details format."""
        response = authenticated_client.post("/api/v1/blueprints/start", json={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

        data = response.json()
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "instance" in data
        assert data["status"] == 422
        assert data["type"].endswith("validation-error")

    def test_validation_error_empty_prompt(self, authenticated_client) -> None:
        """Empty prompt validation should return Problem Details."""
        response = authenticated_client.post("/api/v1/blueprints/start", json={"message": ""})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

        data = response.json()
        assert data["status"] == 422
        assert "validation" in data["title"].lower()
        assert "pydantic" not in data["detail"].lower()
        assert "traceback" not in data["detail"].lower()

    def test_validation_error_prompt_too_long(self, authenticated_client) -> None:
        """Prompt exceeding max length should return Problem Details."""
        long_prompt = "a" * 5000
        response = authenticated_client.post("/api/v1/blueprints/start", json={"message": long_prompt})

        # LangGraph validator might catch this
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

        data = response.json()
        assert data["status"] == 422

    def test_404_returns_problem_details(self, authenticated_client) -> None:
        """404 errors should return Problem Details format."""
        response = authenticated_client.get("/api/v1/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND

        data = response.json()
        assert data["status"] == 404
        assert data["type"].endswith("not-found")
        assert data["instance"] == "/api/v1/nonexistent"

    def test_health_endpoint_success_not_problem_details(self, authenticated_client) -> None:
        """Successful responses should not use Problem Details format."""
        response = authenticated_client.get("/api/v1/health")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
        assert "type" not in data
        assert "title" not in data


class TestProblemDetailsNoInformationLeakage:
    """Test that Problem Details doesn't leak sensitive information."""

    AUTH0_TEST_ENV = {
        "AUTH0__DOMAIN": "test.auth0.com",
        "AUTH0__CLIENT_ID": "test-id",
        "AUTH0__CLIENT_SECRET": "test-secret",
        "AUTH0__AUDIENCE": "test-audience",
    }

    def test_error_does_not_expose_api_keys(self, authenticated_client) -> None:
        """Error responses should not expose API keys."""
        # Note: authenticated_client uses 'test-api-key-12345' from conftest
        response = authenticated_client.post("/api/v1/blueprints/start", json={})

        assert response.status_code == 422
        data = response.json()

        # Check for placeholder key in response
        response_str = str(data).lower()
        assert "test-api-key-12345" not in response_str

    def test_error_does_not_expose_file_paths(self, authenticated_client) -> None:
        """Error responses should not expose internal file paths."""
        response = authenticated_client.post("/api/v1/blueprints/start", json={"message": ""})

        data = response.json()
        response_str = str(data)

        assert "/home/user" not in response_str
        assert "src/ai_agent" not in response_str
        assert ".py" not in response_str

    def test_error_does_not_expose_internal_class_names(self, authenticated_client) -> None:
        """Error responses should not expose internal class names."""
        response = authenticated_client.post("/api/v1/blueprints/start", json={})

        data = response.json()
        response_str = str(data)

        # Standard FastAPI/Starlette errors might use internal names but our handlers should clean them
        assert "PydanticOutputParser" not in response_str
        assert "ChatOpenAI" not in response_str
