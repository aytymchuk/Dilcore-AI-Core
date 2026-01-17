"""Tests for AI agent module."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_agent.exceptions import TemplateParsingError
from ai_agent.schemas.response import TemplateResponse


class TestTemplateAgent:
    """Test cases for TemplateAgent class."""

    @pytest.fixture
    def mock_settings(self):
        """Create mock settings for testing."""
        env_vars = {
            "OPENROUTER__API_KEY": "test-api-key",
            "OPENROUTER__BASE_URL": "https://openrouter.ai/api/v1",
            "OPENROUTER__MODEL": "openai/gpt-oss-20b:free",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            from ai_agent.config.settings import Settings, get_settings
            get_settings.cache_clear()
            yield Settings()

    def test_agent_initializes_with_settings(self, mock_settings) -> None:
        """Agent should initialize with correct settings."""
        from ai_agent.agent.core import TemplateAgent
        
        agent = TemplateAgent(mock_settings)
        
        assert agent._settings == mock_settings
        assert agent._llm is not None
        assert agent._parser is not None

    @pytest.mark.asyncio
    async def test_generate_template_returns_response(self, mock_settings) -> None:
        """generate_template should return TemplateResponse."""
        # Mock the ChatOpenAI class before creating the agent
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = '''{
            "template_id": "test-123",
            "template_name": "Test Template",
            "description": "A test template",
            "status": "draft",
            "metadata": {
                "version": "1.0.0",
                "author": "AI Agent",
                "tags": []
            },
            "sections": []
        }'''
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)
        
        with patch("ai_agent.agent.core.ChatOpenAI", return_value=mock_llm):
            from ai_agent.agent.core import TemplateAgent
            
            agent = TemplateAgent(mock_settings)
            result = await agent.generate_template("Create a test")
            
            assert isinstance(result, TemplateResponse)
            assert result.template_id == "test-123"
            assert result.template_name == "Test Template"

    @pytest.mark.asyncio
    async def test_generate_template_raises_on_invalid_response(self, mock_settings) -> None:
        """generate_template should raise TemplateParsingError on invalid LLM response."""
        # Mock the ChatOpenAI class before creating the agent
        mock_llm = MagicMock()
        mock_response = MagicMock()
        mock_response.content = "This is not valid JSON"
        mock_llm.ainvoke = AsyncMock(return_value=mock_response)

        with patch("ai_agent.agent.core.ChatOpenAI", return_value=mock_llm):
            from ai_agent.agent.core import TemplateAgent

            agent = TemplateAgent(mock_settings)

            with pytest.raises(TemplateParsingError, match="Unable to parse"):
                await agent.generate_template("Create something")


class TestCreateTemplateAgent:
    """Test cases for create_template_agent factory."""

    def test_creates_singleton_instance(self) -> None:
        """create_template_agent should return singleton instance."""
        import ai_agent.agent.core as agent_module
        from ai_agent.config.settings import Settings
        
        # Reset singleton
        agent_module._agent_instance = None
        
        env_vars = {
            "OPENROUTER__API_KEY": "test-key",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            from ai_agent.config.settings import get_settings
            get_settings.cache_clear()
            settings = Settings()
            
            agent1 = agent_module.create_template_agent(settings)
            agent2 = agent_module.create_template_agent(settings)
            
            assert agent1 is agent2
            
            # Cleanup
            agent_module._agent_instance = None
