"""Tests for streaming template generation functionality."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from api.schemas.response import TemplateResponse
from api.schemas.streaming import (
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


class TestBlueprintsGraphStreaming:
    """Tests for BlueprintsGraph streaming functionality."""

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

    @pytest.mark.asyncio
    async def test_generate_stream_yields_events(self, mock_settings) -> None:
        """generate_stream should yield StreamEvent objects."""

        async def mock_astream(*args, **kwargs):
            mock_chunk = MagicMock()
            mock_chunk.content = (
                '```json\n{"template_id": "test-123", "template_name": '
                '"Test", "description": "A test"}\n```\n\n'
                "EXPLANATION:\nThis is a test template."
            )
            mock_chunk.response_metadata = {}
            mock_chunk.additional_kwargs = {}
            yield mock_chunk

        with (
            patch("infrastructure.llm.client.ChatOpenAI") as mock_llm_cls,
            patch("store.vector.faiss_store.FAISS"),
        ):
            mock_llm = MagicMock()
            mock_llm.astream = mock_astream
            mock_llm_cls.return_value = mock_llm

            from agents.blueprints.graph import BlueprintsGraph

            graph = BlueprintsGraph(mock_settings)
            events = []

            async for event in graph.generate_stream("Create a test template"):
                events.append(event)

            assert len(events) >= 3
            event_types = [e.event_type for e in events]
            assert StreamEventType.CONTENT in event_types
            assert StreamEventType.TEMPLATE in event_types
            assert StreamEventType.DONE in event_types

    @pytest.mark.asyncio
    async def test_generate_stream_handles_error(self, mock_settings) -> None:
        """generate_stream should yield error event on failure."""

        async def mock_astream_error(*args, **kwargs):
            raise ValueError("API Error")
            yield  # noqa: unreachable

        with (
            patch("infrastructure.llm.client.ChatOpenAI") as mock_llm_cls,
            patch("store.vector.faiss_store.FAISS"),
        ):
            mock_llm = MagicMock()
            mock_llm.astream = mock_astream_error
            mock_llm_cls.return_value = mock_llm

            from agents.blueprints.graph import BlueprintsGraph

            graph = BlueprintsGraph(mock_settings)
            events = []

            async for event in graph.generate_stream("Create something"):
                events.append(event)

            assert len(events) >= 1
            assert events[-1].event_type == StreamEventType.ERROR
