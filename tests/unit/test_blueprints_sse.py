"""Unit tests for Blueprints SSE streaming helpers and route registration."""

import json

from langchain_core.messages import AIMessageChunk

from agents.blueprints.constants import (
    ASK_ROUTE,
    DESIGN_ROUTE,
    GENERATE_ROUTE,
    IDENTIFY_INTENT_ROUTE,
)
from application.services.blueprints_service import (
    _NODE_STATUS_MAP,
    EXPECTED_STREAM_STATUS_NODES,
    _parse_langgraph_stream_chunk,
    _reasoning_delta_from_message_chunk,
    _sse_event,
    _text_token_delta_from_message_chunk,
)
from main import app


class TestStreamHelpers:
    """Tests for SSE / LangGraph stream normalization helpers."""

    def test_parse_tuple_chunk(self) -> None:
        parsed = _parse_langgraph_stream_chunk(("updates", {"n": {"x": 1}}))
        assert parsed is not None
        mode, data = parsed
        assert mode == "updates"
        assert data == {"n": {"x": 1}}

    def test_parse_v2_dict_chunk(self) -> None:
        parsed = _parse_langgraph_stream_chunk({"type": "messages", "data": ("m", {})})
        assert parsed == ("messages", ("m", {}))

    def test_parse_invalid_returns_none(self) -> None:
        assert _parse_langgraph_stream_chunk("bad") is None

    def test_text_token_delta_string(self) -> None:
        chunk = AIMessageChunk(content="hello")
        assert _text_token_delta_from_message_chunk(chunk) == "hello"

    def test_text_token_delta_list_text_block(self) -> None:
        chunk = AIMessageChunk(content=[{"type": "text", "text": "a"}])
        assert _text_token_delta_from_message_chunk(chunk) == "a"

    def test_reasoning_from_additional_kwargs(self) -> None:
        chunk = AIMessageChunk(content="", additional_kwargs={"reasoning_content": "think"})
        assert _reasoning_delta_from_message_chunk(chunk) == "think"

    def test_reasoning_from_thinking_block(self) -> None:
        chunk = AIMessageChunk(content=[{"type": "thinking", "thinking": "step"}])
        assert _reasoning_delta_from_message_chunk(chunk) == "step"

    def test_sse_event_json(self) -> None:
        evt = _sse_event({"category": "data", "thread_id": "t1", "messages": []})
        assert "data" in evt
        payload = json.loads(evt["data"])
        assert payload["category"] == "data"
        assert payload["thread_id"] == "t1"

    def test_node_status_map_covers_supervisor_and_inner_nodes(self) -> None:
        """Streaming status events require a mapping for every user-visible graph node."""
        required = frozenset(
            {
                "supervisor",
                ASK_ROUTE,
                DESIGN_ROUTE,
                GENERATE_ROUTE,
                IDENTIFY_INTENT_ROUTE,
                "ask_agent",
                "design_agent",
                "update_design_context",
                "build_plan",
                "present_plan",
                "collect_response",
                "handle_response",
                "write_success",
            }
        )
        assert required <= frozenset(_NODE_STATUS_MAP.keys())
        assert frozenset(_NODE_STATUS_MAP.keys()) == EXPECTED_STREAM_STATUS_NODES


class TestBlueprintsSseOpenApi:
    """Ensure SSE endpoints are registered (avoids hanging TestClient on long-lived SSE)."""

    def test_openapi_lists_stream_endpoints(self) -> None:
        schema = app.openapi()
        paths = schema["paths"]
        assert "/api/v1/blueprints/start-stream" in paths
        assert "/api/v1/blueprints/{thread_id}/continue-stream" in paths
        assert "/api/v1/blueprints/{thread_id}/resume-stream" in paths

    def test_openapi_stream_success_uses_text_event_stream(self) -> None:
        schema = app.openapi()
        paths = schema["paths"]
        start = paths["/api/v1/blueprints/start-stream"]["post"]["responses"]
        assert "text/event-stream" in start["201"]["content"]
        cont = paths["/api/v1/blueprints/{thread_id}/continue-stream"]["post"]["responses"]
        assert "text/event-stream" in cont["200"]["content"]
        resume = paths["/api/v1/blueprints/{thread_id}/resume-stream"]["post"]["responses"]
        assert "text/event-stream" in resume["200"]["content"]

    def test_openapi_includes_blueprint_sse_event_schema(self) -> None:
        schema = app.openapi()
        components = schema["components"]["schemas"]
        assert "BlueprintSseEvent" in components
        root = components["BlueprintSseEvent"]
        assert "oneOf" in root
        assert root.get("discriminator", {}).get("propertyName") == "category"
