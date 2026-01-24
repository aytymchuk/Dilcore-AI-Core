"""Tests for streaming template generation functionality."""

import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from ai_agent.schemas.streaming import (
    StreamEvent,
    StreamEventType,
    StreamingTemplateResponse,
)


class TestStreamEventModels:
    """Test cases for streaming event Pydantic models."""

    def test_stream_event_serialization(self) -> None:
        """StreamEvent should serialize to JSON correctly."""
        event = StreamEvent(
            event_type=StreamEventType.CONTENT,
            data="Processing your request...",
        )

        json_str = event.model_dump_json()
        parsed = json.loads(json_str)

        assert parsed["event_type"] == "content"
        assert parsed["data"] == "Processing your request..."
        assert "timestamp" in parsed

    def test_stream_event_thinking_type(self) -> None:
        """StreamEvent should support thinking event type."""
        event = StreamEvent(
            event_type=StreamEventType.THINKING,
            data="Let me analyze this...",
        )

        assert event.event_type == StreamEventType.THINKING
        assert event.data == "Let me analyze this..."

    def test_stream_event_template_type_with_dict(self) -> None:
        """StreamEvent should accept dict data for template type."""
        template_data = {
            "template": {"template_id": "test-123"},
            "explanation": "This template is designed for...",
        }

        event = StreamEvent(
            event_type=StreamEventType.TEMPLATE,
            data=template_data,
        )

        assert event.event_type == StreamEventType.TEMPLATE
        assert event.data["template"]["template_id"] == "test-123"

    def test_all_event_types_exist(self) -> None:
        """All required event types should be defined."""
        assert StreamEventType.THINKING == "thinking"
        assert StreamEventType.CONTENT == "content"
        assert StreamEventType.TEMPLATE == "template"
        assert StreamEventType.ERROR == "error"
        assert StreamEventType.DONE == "done"


class TestStreamingTemplateResponse:
    """Test cases for StreamingTemplateResponse model."""

    def test_streaming_response_with_template(self) -> None:
        """StreamingTemplateResponse should contain template and explanation."""
        from ai_agent.schemas.response import TemplateResponse

        template = TemplateResponse(
            template_id="test-001",
            template_name="Test Template",
            description="A test template",
        )

        response = StreamingTemplateResponse(
            template=template,
            explanation="This template provides basic structure.",
        )

        assert response.template.template_id == "test-001"
        assert response.explanation == "This template provides basic structure."


class TestStreamingModuleBuilderAgent:
    """Test cases for StreamingModuleBuilderAgent class (formerly StreamingTemplateAgent)."""

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

    @pytest.mark.asyncio
    async def test_generate_template_stream_yields_events(self, mock_settings) -> None:
        """generate_template_stream should yield StreamEvent objects."""
        
        async def mock_astream(*args, **kwargs):
            """Mock async generator for astream."""
            mock_chunk = MagicMock()
            mock_chunk.content = (
                '```json\n{"template_id": "test-123", "template_name": '
                '"Test", "description": "A test"}\n```\n\n'
                "EXPLANATION:\nThis is a test template."
            )
            mock_chunk.response_metadata = {}
            mock_chunk.additional_kwargs = {}
            yield mock_chunk

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream
        
        with patch("langchain_openai.ChatOpenAI", return_value=mock_llm):
            from ai_agent.agent.streaming import StreamingModuleBuilderAgent

            agent = StreamingModuleBuilderAgent(mock_settings)
            events = []

            async for event in agent.generate_template_stream("Create a test template"):
                events.append(event)

            # Should have at least content, template, and done events
            assert len(events) >= 3
            event_types = [e.event_type for e in events]
            assert StreamEventType.CONTENT in event_types
            assert StreamEventType.TEMPLATE in event_types
            assert StreamEventType.DONE in event_types

    @pytest.mark.asyncio
    async def test_generate_template_stream_handles_error(self, mock_settings) -> None:
        """generate_template_stream should yield error event on failure."""
        
        async def mock_astream_error(*args, **kwargs):
            """Mock async generator that raises error."""
            raise ValueError("API Error")
            yield  # Make it a generator

        mock_llm = MagicMock()
        mock_llm.astream = mock_astream_error
        
        with patch("langchain_openai.ChatOpenAI", return_value=mock_llm):
            from ai_agent.agent.streaming import StreamingModuleBuilderAgent

            agent = StreamingModuleBuilderAgent(mock_settings)
            events = []

            async for event in agent.generate_template_stream("Create something"):
                events.append(event)

            # Should have error event
            assert len(events) >= 1
            assert events[-1].event_type == StreamEventType.ERROR
            # Error messages are sanitized to not expose internal details
            assert "error occurred" in events[-1].data.lower()

    @pytest.mark.asyncio
    async def test_parse_response_extracts_template_and_explanation(
        self, mock_settings
    ) -> None:
        """_parse_response should extract template JSON and explanation."""
        mock_llm = MagicMock()
        
        with patch("langchain_openai.ChatOpenAI", return_value=mock_llm):
            from ai_agent.agent.streaming import StreamingModuleBuilderAgent

            agent = StreamingModuleBuilderAgent(mock_settings)

            content = """Here is the template:

```json
{
    "template_id": "usr-reg-001",
    "template_name": "User Registration",
    "description": "User registration form template"
}
```

EXPLANATION:
This template provides a basic structure for user registration with essential fields.
It follows best practices for form design."""

            result = agent._parse_response(content)

            assert result.template.template_id == "usr-reg-001"
            assert result.template.template_name == "User Registration"
            assert "basic structure" in result.explanation


class TestCreateStreamingTemplateAgent:
    """Test cases for create_streaming_template_agent factory."""

    def test_creates_singleton_instance(self) -> None:
        """create_streaming_template_agent should return singleton instance."""
        import ai_agent.agent.streaming as streaming_module

        # Reset singleton
        streaming_module._streaming_agent_instance = None

        env_vars = {
            "OPENROUTER__API_KEY": "test-key",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            from ai_agent.config.settings import Settings, get_settings

            get_settings.cache_clear()
            settings = Settings()

            agent1 = streaming_module.create_streaming_template_agent(settings)
            agent2 = streaming_module.create_streaming_template_agent(settings)

            assert agent1 is agent2

            # Cleanup
            streaming_module._streaming_agent_instance = None
