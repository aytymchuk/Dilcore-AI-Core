"""Tests for AI agent (BlueprintsGraph) module."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from api.schemas.response import TemplateResponse


class TestBlueprintsGraph:
    """Test cases for BlueprintsGraph class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        env_vars = {
            "OPENROUTER__API_KEY": "test-api-key",
            "OPENROUTER__BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER__MODEL": "openai/gpt-oss-20b:free",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            from shared.config.settings import Settings, get_settings

            get_settings.cache_clear()
            yield Settings()

    def test_graph_initializes_with_settings(self, mock_settings) -> None:
        """BlueprintsGraph should initialize with correct settings."""
        with (
            patch("infrastructure.llm.client.ChatOpenAI"),
            patch("infrastructure.llm.client.OpenAIEmbeddings"),
            patch("store.vector.faiss_store.FAISS"),
        ):
            from agents.blueprints.graph import BlueprintsGraph

            graph = BlueprintsGraph(mock_settings)

            assert graph._settings == mock_settings
            assert graph._llm is not None
            assert graph._streaming_llm is not None

    @pytest.mark.asyncio
    async def test_generate_returns_template_response(self, mock_settings) -> None:
        """generate() should return TemplateResponse."""
        mock_template = TemplateResponse(
            template_id="test-123",
            template_name="Test Template",
            description="A test template",
        )

        with (
            patch("infrastructure.llm.client.ChatOpenAI"),
            patch("infrastructure.llm.client.OpenAIEmbeddings"),
            patch("store.vector.faiss_store.FAISS"),
        ):
            from agents.blueprints.graph import BlueprintsGraph

            graph = BlueprintsGraph(mock_settings)

            # Patch the compiled graph's ainvoke
            graph._graph = MagicMock()
            graph._graph.ainvoke = AsyncMock(
                return_value={
                    "template_response": mock_template,
                    "error": None,
                }
            )

            result = await graph.generate("Create a test")

            assert isinstance(result, TemplateResponse)
            assert result.template_id == "test-123"
            assert result.template_name == "Test Template"

    def test_context_management(self, mock_settings) -> None:
        """Context entities should accumulate and be clearable."""
        with (
            patch("infrastructure.llm.client.ChatOpenAI"),
            patch("infrastructure.llm.client.OpenAIEmbeddings"),
            patch("store.vector.faiss_store.FAISS"),
        ):
            from agents.blueprints.graph import BlueprintsGraph

            graph = BlueprintsGraph(mock_settings)

            # Manually add a context entity
            graph._context_entities.append({"id": "entity-1", "name": "Entity 1"})

            assert len(graph.get_context_entities()) == 1

            graph.clear_context()
            assert len(graph.get_context_entities()) == 0


class TestBlueprintsService:
    """Test cases for BlueprintsService orchestration."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        env_vars = {"OPENROUTER__API_KEY": "test-api-key"}
        with patch.dict(os.environ, env_vars, clear=False):
            from shared.config.settings import Settings, get_settings

            get_settings.cache_clear()
            yield Settings()

    @pytest.mark.asyncio
    async def test_service_generate_delegates_to_graph(self, mock_settings) -> None:
        """BlueprintsService.generate_template should call the graph."""
        mock_template = TemplateResponse(
            template_id="svc-001",
            template_name="Service Template",
            description="Test",
        )

        with patch("application.services.blueprints_service.BlueprintsGraph") as mock_graph_cls:
            mock_graph = MagicMock()
            mock_graph.generate = AsyncMock(return_value=mock_template)
            mock_graph.get_context_entities.return_value = []
            mock_graph_cls.return_value = mock_graph

            from application.services.blueprints_service import BlueprintsService

            service = BlueprintsService(mock_settings)
            result = await service.generate_template("Create something")

            assert isinstance(result, TemplateResponse)
            assert result.template_id == "svc-001"
            mock_graph.generate.assert_called_once_with("Create something")
