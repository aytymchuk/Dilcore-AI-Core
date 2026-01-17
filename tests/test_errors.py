"""Tests for Problem Details error handling."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError as PydanticValidationError

from ai_agent.exceptions import (
    AIAgentException,
    ConfigurationError,
    LLMProviderError,
    TemplateGenerationError,
    TemplateParsingError,
    ValidationError,
)
from ai_agent.schemas.errors import ProblemDetails


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
                status=200,  # Invalid: not an error status
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

    def test_template_generation_error_defaults(self) -> None:
        """TemplateGenerationError should have correct defaults."""
        exc = TemplateGenerationError()

        assert exc.message == "Failed to generate template"
        assert exc.problem_type == "generation-error"
        assert exc.title == "Template Generation Error"
        assert exc.status_code == 500

    def test_llm_provider_error_defaults(self) -> None:
        """LLMProviderError should have correct defaults."""
        exc = LLMProviderError()

        assert exc.message == "LLM provider communication failed"
        assert exc.problem_type == "llm-provider-error"
        assert exc.title == "LLM Provider Error"
        assert exc.status_code == 502

    def test_template_parsing_error_defaults(self) -> None:
        """TemplateParsingError should have correct defaults."""
        exc = TemplateParsingError()

        assert exc.message == "Failed to parse template response"
        assert exc.problem_type == "parsing-error"
        assert exc.title == "Template Parsing Error"
        assert exc.status_code == 500

    def test_configuration_error_defaults(self) -> None:
        """ConfigurationError should have correct defaults."""
        exc = ConfigurationError("Missing API key")

        assert exc.message == "Missing API key"
        assert exc.problem_type == "configuration-error"
        assert exc.title == "Configuration Error"
        assert exc.status_code == 500

    def test_base_exception_inheritance(self) -> None:
        """All custom exceptions should inherit from AIAgentException."""
        assert isinstance(ValidationError("test"), AIAgentException)
        assert isinstance(TemplateGenerationError(), AIAgentException)
        assert isinstance(LLMProviderError(), AIAgentException)
        assert isinstance(TemplateParsingError(), AIAgentException)
        assert isinstance(ConfigurationError("test"), AIAgentException)


class TestGlobalExceptionHandlers:
    """Test cases for global exception handlers."""

    @pytest.fixture
    def client(self):
        """Create test client with mocked settings."""
        env_vars = {
            "OPENROUTER__API_KEY": "test-api-key",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            from ai_agent.config.settings import get_settings

            get_settings.cache_clear()
            from ai_agent.main import app

            yield TestClient(app)

    def test_validation_error_returns_problem_details(self, client) -> None:
        """Validation errors should return Problem Details format."""
        # Send request with missing prompt field
        response = client.post("/api/v1/metadata/generate", json={})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()
        assert "type" in data
        assert "title" in data
        assert "status" in data
        assert "detail" in data
        assert "instance" in data

        assert data["status"] == 422
        assert data["type"].endswith("validation-error")
        assert "prompt" in data["detail"].lower()

    def test_validation_error_empty_prompt(self, client) -> None:
        """Empty prompt validation should return Problem Details."""
        response = client.post("/api/v1/metadata/generate", json={"prompt": ""})

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()
        assert data["status"] == 422
        assert "validation" in data["title"].lower()
        # Should not expose internal error details
        assert "pydantic" not in data["detail"].lower()
        assert "traceback" not in data["detail"].lower()

    def test_validation_error_prompt_too_long(self, client) -> None:
        """Prompt exceeding max length should return Problem Details."""
        long_prompt = "a" * 5000  # Exceeds 4000 character limit
        response = client.post(
            "/api/v1/metadata/generate", json={"prompt": long_prompt}
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        data = response.json()
        assert data["status"] == 422
        assert data["instance"] == "/api/v1/metadata/generate"

    def test_llm_provider_error_returns_problem_details(self, client) -> None:
        """LLM provider errors should return Problem Details format."""
        from openai import APIConnectionError

        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(
            side_effect=APIConnectionError(request=MagicMock())
        )

        with patch("ai_agent.agent.core.ChatOpenAI", return_value=mock_llm):
            # Need to reload to pick up the mocked ChatOpenAI
            import ai_agent.agent.core as agent_module

            agent_module._agent_instance = None

            response = client.post(
                "/api/v1/metadata/generate", json={"prompt": "Create a template"}
            )

            # Clean up
            agent_module._agent_instance = None

        assert response.status_code == status.HTTP_502_BAD_GATEWAY

        data = response.json()
        assert data["status"] == 502
        assert data["type"].endswith("llm-provider-error")
        assert data["title"] == "LLM Provider Error"
        # Should not expose internal error details
        assert "APIConnectionError" not in data["detail"]
        assert "provider" in data["detail"].lower() or "ai" in data["detail"].lower()

    def test_parsing_error_returns_problem_details(self, client) -> None:
        """Template parsing errors should return Problem Details format."""
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "Invalid JSON response"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("ai_agent.agent.core.ChatOpenAI", return_value=mock_llm):
            import ai_agent.agent.core as agent_module

            agent_module._agent_instance = None

            response = client.post(
                "/api/v1/metadata/generate", json={"prompt": "Create a template"}
            )

            agent_module._agent_instance = None

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        data = response.json()
        assert data["status"] == 500
        assert data["type"].endswith("parsing-error")
        # Should not expose parsing details
        assert "json" not in data["detail"].lower()
        assert "parse" in data["detail"].lower()

    def test_unhandled_exception_returns_generic_error(self, client) -> None:
        """Unhandled exceptions should return generic Problem Details."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=RuntimeError("Unexpected error"))

        with patch("ai_agent.agent.core.ChatOpenAI", return_value=mock_llm):
            import ai_agent.agent.core as agent_module

            agent_module._agent_instance = None

            response = client.post(
                "/api/v1/metadata/generate", json={"prompt": "Create a template"}
            )

            agent_module._agent_instance = None

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        data = response.json()
        assert data["status"] == 500
        assert data["type"].endswith("generation-error")
        # Should not expose internal exception details
        assert "RuntimeError" not in data["detail"]
        assert "Unexpected error" not in data["detail"]
        assert "unexpected" in data["detail"].lower() or "error" in data["detail"].lower()

    def test_404_returns_problem_details(self, client) -> None:
        """404 errors should return Problem Details format."""
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == status.HTTP_404_NOT_FOUND

        data = response.json()
        assert data["status"] == 404
        assert data["type"].endswith("not-found")
        assert data["instance"] == "/api/v1/nonexistent"

    def test_health_endpoint_success_not_problem_details(self, client) -> None:
        """Successful responses should not use Problem Details format."""
        response = client.get("/api/v1/health")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        # Should be normal response, not Problem Details
        assert "status" in data
        assert data["status"] == "healthy"
        assert "type" not in data  # Not a Problem Details response
        assert "title" not in data


class TestProblemDetailsNoInformationLeakage:
    """Test that Problem Details doesn't leak sensitive information."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        env_vars = {
            "OPENROUTER__API_KEY": "secret-api-key-12345",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            from ai_agent.config.settings import get_settings

            get_settings.cache_clear()
            from ai_agent.main import app

            yield TestClient(app)

    def test_error_does_not_expose_api_keys(self, client) -> None:
        """Error responses should not expose API keys."""
        response = client.post("/api/v1/metadata/generate", json={})

        assert response.status_code == 422
        data = response.json()

        # Check that sensitive information is not in the response
        response_str = str(data).lower()
        assert "secret-api-key" not in response_str
        assert "12345" not in response_str

    def test_error_does_not_expose_file_paths(self, client) -> None:
        """Error responses should not expose internal file paths."""
        response = client.post("/api/v1/metadata/generate", json={"prompt": ""})

        data = response.json()
        response_str = str(data)

        # Should not contain file system paths
        assert "/home/user" not in response_str
        assert "src/ai_agent" not in response_str
        assert ".py" not in response_str

    def test_error_does_not_expose_stack_traces(self, client) -> None:
        """Error responses should not expose stack traces."""
        mock_llm = MagicMock()
        mock_llm.ainvoke = AsyncMock(side_effect=Exception("Internal error"))

        with patch("ai_agent.agent.core.ChatOpenAI", return_value=mock_llm):
            import ai_agent.agent.core as agent_module

            agent_module._agent_instance = None

            response = client.post(
                "/api/v1/metadata/generate", json={"prompt": "Test"}
            )

            agent_module._agent_instance = None

        data = response.json()
        response_str = str(data).lower()

        # Should not contain stack trace elements
        assert "traceback" not in response_str
        assert "file " not in response_str
        assert "line " not in response_str

    def test_error_does_not_expose_internal_class_names(self, client) -> None:
        """Error responses should not expose internal class names."""
        response = client.post("/api/v1/metadata/generate", json={})

        data = response.json()
        response_str = str(data)

        # Should not contain internal class names
        assert "PydanticOutputParser" not in response_str
        assert "ChatOpenAI" not in response_str
        assert "TemplateAgent" not in response_str
