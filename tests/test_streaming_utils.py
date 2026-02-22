"""Tests for shared streaming utilities."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessageChunk
from langchain_core.output_parsers import PydanticOutputParser

from api.schemas.response import TemplateResponse
from api.schemas.streaming import StreamEvent, StreamEventType, StreamingTemplateResponse
from shared.exceptions import TemplateParsingError
from shared.streaming.emitter import StreamEmitter
from shared.streaming.utils import format_sse_event, is_thinking_chunk, parse_streaming_response


@pytest.fixture
def mock_template_response() -> TemplateResponse:
    from api.schemas.response import TemplateField, TemplateMetadata, TemplateSection, TemplateStatus

    return TemplateResponse(
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


# ------------------------------------------------------------------
# Utils Tests
# ------------------------------------------------------------------


class TestStreamingUtils:
    def test_is_thinking_chunk_metadata(self):
        """Detect thinking based on response_metadata."""
        # OpenRouter/Anthropic style
        chunk = AIMessageChunk(content="", response_metadata={"thinking": True})
        assert is_thinking_chunk(chunk) is True

        chunk2 = AIMessageChunk(content="", response_metadata={"reasoning": True})
        assert is_thinking_chunk(chunk2) is True

    def test_is_thinking_chunk_kwargs(self):
        """Detect thinking based on additional_kwargs."""
        # Standard OpenAI-compat style
        chunk = AIMessageChunk(content="", additional_kwargs={"is_thinking": True})
        assert is_thinking_chunk(chunk) is True

        chunk2 = AIMessageChunk(content="", additional_kwargs={"thinking": "some thought process"})
        assert is_thinking_chunk(chunk2) is True

    def test_is_not_thinking_chunk(self):
        """Normal chunks are not thinking."""
        chunk = AIMessageChunk(content="Hello", response_metadata={"model": "gpt-4"}, additional_kwargs={})
        assert is_thinking_chunk(chunk) is False

    def test_parse_streaming_response_success(self, mock_template_response: TemplateResponse):
        """Parse fallback plain JSON successfully."""
        mock_parser = Mock(spec=PydanticOutputParser)
        mock_parser.parse.return_value = mock_template_response

        content = '{"template_id": "test"}\n\nEXPLANATION:\nThis is a test.'
        response = parse_streaming_response(content, mock_parser)

        assert isinstance(response, StreamingTemplateResponse)
        assert response.template == mock_template_response
        assert response.explanation == "This is a test."
        mock_parser.parse.assert_called_once_with(content)

    def test_parse_streaming_response_json_fence(self, mock_template_response: TemplateResponse):
        """Parse JSON directly from a markdown fence."""
        mock_parser = Mock(spec=PydanticOutputParser)

        json_content = mock_template_response.model_dump_json()
        content = f"```json\n{json_content}\n```\nEXPLANATION: Fence parsed."

        response = parse_streaming_response(content, mock_parser)

        assert response.template.template_id == mock_template_response.template_id
        assert response.explanation == "Fence parsed."
        mock_parser.parse.assert_not_called()

    def test_parse_streaming_response_error(self):
        """Parsing failure raises TemplateParsingError."""
        mock_parser = Mock(spec=PydanticOutputParser)
        mock_parser.parse.side_effect = Exception("Internal parse error")

        with pytest.raises(TemplateParsingError, match="Unable to parse the generated template response"):
            parse_streaming_response("invalid garbage", mock_parser)

    def test_format_sse_event(self):
        """Events are formatted correctly for Server-Sent Events."""
        event = StreamEvent(event_type=StreamEventType.CONTENT, data="hello")
        sse_str = format_sse_event(event)

        assert sse_str.startswith("data: ")
        assert sse_str.endswith("\n\n")

        parsed = json.loads(sse_str.removeprefix("data: ").removesuffix("\n\n"))
        assert parsed["event_type"] == "content"
        assert parsed["data"] == "hello"


# ------------------------------------------------------------------
# StreamEmitter Tests
# ------------------------------------------------------------------


class TestStreamEmitter:
    @pytest.fixture
    def mock_parser(self, mock_template_response: TemplateResponse) -> Mock:
        parser = Mock(spec=PydanticOutputParser)
        parser.parse.return_value = mock_template_response
        return parser

    async def test_stream_thinking_and_content(self, mock_parser: Mock):
        """Emitter transitions correctly from thinking to content to done."""

        async def mock_astream(*args, **kwargs):
            yield AIMessageChunk(content="thought 1", additional_kwargs={"is_thinking": True})
            yield AIMessageChunk(content="thought 2", additional_kwargs={"is_thinking": True})
            # Transition to content
            yield AIMessageChunk(content="```json\n")
            yield AIMessageChunk(
                content='{"template_id": "t1", "template_name": "T1", "description": "test", "status": "draft", "metadata": {}, "sections": []}'
            )
            yield AIMessageChunk(content="\n```\nEXPLANATION: Done.")

        mock_llm = AsyncMock()
        mock_llm.astream = mock_astream

        emitter = StreamEmitter(mock_llm, [], mock_parser)
        events = [e async for e in emitter.stream()]

        assert len(events) == 7
        assert events[0].event_type == StreamEventType.THINKING
        assert events[0].data == "thought 1"
        assert events[1].event_type == StreamEventType.THINKING
        assert events[2].event_type == StreamEventType.CONTENT
        assert events[3].event_type == StreamEventType.CONTENT

        # Last two events are TEMPLATE and DONE
        assert events[5].event_type == StreamEventType.TEMPLATE
        assert events[6].event_type == StreamEventType.DONE

    async def test_stream_provider_error(self, mock_parser: Mock):
        """APIError yields an ERROR event instead of crashing."""
        from openai import APIError

        async def mock_astream(*args, **kwargs):
            yield AIMessageChunk(content="start")
            raise APIError("Provider is down", request=Mock(), body=None)

        mock_llm = AsyncMock()
        mock_llm.astream = mock_astream

        emitter = StreamEmitter(mock_llm, [], mock_parser)
        events = [e async for e in emitter.stream()]

        assert len(events) == 2
        assert events[0].event_type == StreamEventType.CONTENT
        assert events[1].event_type == StreamEventType.ERROR
        assert events[1].data == "Unable to communicate with AI provider"

    async def test_stream_parsing_error(self):
        """Parsing failure yields an ERROR event."""

        async def mock_astream(*args, **kwargs):
            yield AIMessageChunk(content="invalid output")

        mock_llm = AsyncMock()
        mock_llm.astream = mock_astream

        mock_parser = Mock(spec=PydanticOutputParser)
        mock_parser.parse.side_effect = Exception("bad json")

        emitter = StreamEmitter(mock_llm, [], mock_parser)
        events = [e async for e in emitter.stream()]

        assert len(events) == 2
        assert events[0].event_type == StreamEventType.CONTENT
        assert events[1].event_type == StreamEventType.ERROR
        assert events[1].data == "Streaming generation failed"
