"""Tests for API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from ai_agent.schemas.response import (
    TemplateField,
    TemplateMetadata,
    TemplateResponse,
    TemplateSection,
    TemplateStatus,
)


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


class TestGenerateEndpoint:
    """Test cases for template generation endpoint."""

    def test_generate_validates_empty_prompt(self, test_client: TestClient) -> None:
        """Generate should reject empty prompts."""
        response = test_client.post(
            "/api/v1/metadata/generate",
            json={"prompt": ""},
        )
        
        assert response.status_code == 422  # Validation error

    def test_generate_validates_missing_prompt(self, test_client: TestClient) -> None:
        """Generate should reject missing prompt field."""
        response = test_client.post(
            "/api/v1/metadata/generate",
            json={},
        )
        
        assert response.status_code == 422  # Validation error

    def test_generate_returns_structured_response(
        self, test_client: TestClient
    ) -> None:
        """Generate should return structured TemplateResponse."""
        # Create mock template response
        mock_template = TemplateResponse(
            template_id="test-001",
            template_name="Test Template",
            description="A test template",
            status=TemplateStatus.DRAFT,
            metadata=TemplateMetadata(),
            sections=[
                TemplateSection(
                    section_id="section-1",
                    title="Test Section",
                    fields=[
                        TemplateField(
                            name="test_field",
                            type="string",
                            required=True,
                        )
                    ],
                )
            ],
        )

        # Mock the agent's generate_template method
        with patch(
            "ai_agent.api.dependencies.create_template_agent"
        ) as mock_create_agent:
            mock_agent = AsyncMock()
            mock_agent.generate_template.return_value = mock_template
            mock_create_agent.return_value = mock_agent

            response = test_client.post(
                "/api/v1/metadata/generate",
                json={"prompt": "Create a test template"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["template_id"] == "test-001"
            assert data["template_name"] == "Test Template"
            assert len(data["sections"]) == 1


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
