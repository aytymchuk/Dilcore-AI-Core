"""Integration tests for AI agent (BlueprintsGraph) module.

Requires Docker — a real MongoDB instance is provided by testcontainers.
"""

import os
from unittest.mock import patch

import pytest


@pytest.mark.integration
class TestBlueprintsGraph:
    """Test cases for BlueprintsGraph class with real MongoDB."""

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
            get_settings.cache_clear()

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
