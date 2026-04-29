"""Unit tests for Blueprints SSE streaming helpers and route registration."""

import json

import pytest
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
    _graph_progress_thinking_sse,
    _parse_langgraph_stream_chunk,
    _sse_event,
)
from main import app
from shared.reasoning import (
    ReasoningBuffer,
    SupervisorStructuredCaptureState,
    add_step,
    consume_supervisor_structured_delta,
    extract_reasoning_delta,
    extract_text_delta,
    reset_reasoning_buffer,
    set_header,
    set_reasoning_buffer,
    with_reasoning_node,
    with_step,
)


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
        assert extract_text_delta(chunk) == "hello"

    def test_text_token_delta_list_text_block(self) -> None:
        chunk = AIMessageChunk(content=[{"type": "text", "text": "a"}])
        assert extract_text_delta(chunk) == "a"

    def test_reasoning_from_additional_kwargs(self) -> None:
        chunk = AIMessageChunk(content="", additional_kwargs={"reasoning_content": "think"})
        assert extract_reasoning_delta(chunk) == ("reasoning", "think")

    def test_reasoning_from_thinking_block(self) -> None:
        chunk = AIMessageChunk(content=[{"type": "thinking", "thinking": "step"}])
        assert extract_reasoning_delta(chunk) == ("thinking", "step")

    def test_supervisor_structured_json_suppressed_until_parse(self) -> None:
        """Chunked like LLM token streams; avoid single-character splits (brief ``{}`` is ambiguous)."""
        st = SupervisorStructuredCaptureState()
        parts = [
            '{\n  "reasoning": "because ask", ',
            '"decision": {"next_route": "ask"}}\n',
        ]
        effects_acc: list[dict] = []
        emitted: list[str | None] = []
        for p in parts:
            emit, eff = consume_supervisor_structured_delta(st, p, agent_type=None)
            effects_acc.extend(eff)
            emitted.append(emit)
        assert all(e is None for e in emitted)
        kinds = [e["kind"] for e in effects_acc]
        assert kinds == ["supervisor_stream_start", "supervisor_stream_parsed"]
        assert effects_acc[-1]["next_route"] == "ask"
        assert effects_acc[-1]["reasoning"] == "because ask"

    def test_supervisor_structured_then_plain_after_json(self) -> None:
        st = SupervisorStructuredCaptureState()
        json_part = '{"reasoning": "r", "decision": {"next_route": "ask"}}'
        md = "\n# Hello"
        emit1, e1 = consume_supervisor_structured_delta(st, json_part + md, agent_type=None)
        assert emit1 == "\n# Hello"
        assert any(e["kind"] == "supervisor_stream_parsed" for e in e1)

    def test_agent_type_flushes_capture(self) -> None:
        st = SupervisorStructuredCaptureState()
        st.buf = "{"
        st.capturing = True
        emit, _ = consume_supervisor_structured_delta(st, "rest", agent_type="ask")
        assert emit == "{rest"

    def test_reasoning_envelope_concat_until_text_delta(self) -> None:
        buf = ReasoningBuffer(thread_id="t1", anchor_message_id="m-0", sequence_base=0)

        env1 = buf.add_provider_delta("reasoning", "a")
        env2 = buf.add_provider_delta("reasoning", "b")
        assert env1.id == env2.id
        assert env2.steps[-1].content == "ab"
        assert env2.steps[-1].status == "running"

        buf.close_on_text_delta(new_anchor_message_id="m-1")
        env3 = buf.add_provider_delta("reasoning", "c")
        assert env3.id != env2.id
        assert env3.after_message_id == "m-1"

    def test_assistant_reply_delta_merges_and_finalize_completes_running(self) -> None:
        buf = ReasoningBuffer(thread_id="t1", anchor_message_id="m-0", sequence_base=0)
        buf.close_on_text_delta(new_anchor_message_id="m-1")
        env1 = buf.add_assistant_reply_delta("Hel")
        env2 = buf.add_assistant_reply_delta("lo")
        assert env1.id == env2.id
        assert env2.steps[-1].content == "Hello"
        assert env2.steps[-1].status == "running"
        buf.finalize_streaming_steps(success=True)
        assert buf.envelopes()[-1].steps[-1].status == "completed"

    def test_finalize_streaming_steps_failure_marks_running_failed(self) -> None:
        buf = ReasoningBuffer(thread_id="t1", anchor_message_id="m-0", sequence_base=0)
        buf.add_provider_delta("reasoning", "x", status="running")
        buf.finalize_streaming_steps(success=False)
        assert buf.envelopes()[0].steps[-1].status == "failed"

    def test_graph_progress_maps_to_thinking_sse_payload(self) -> None:
        buf = ReasoningBuffer(thread_id="t1", anchor_message_id="m-0", sequence_base=0)
        payload = _graph_progress_thinking_sse(buf, "supervisor")
        assert payload is not None
        assert payload["category"] == "thinking"
        assert payload["status"] == "completed"
        assert payload["phase"] == "routing"
        assert payload["node"] == "supervisor"
        assert buf.envelopes()[0].steps[0].status == "completed"

    @pytest.mark.asyncio
    async def test_reasoning_node_wrapper_supplies_node_attribution(self) -> None:
        async def node(_state: dict) -> dict:
            add_step("Wrapped node step", status="completed")
            return {"done": True}

        buf = ReasoningBuffer(thread_id="t1", anchor_message_id="m-0", sequence_base=0)
        token = set_reasoning_buffer(buf)
        try:
            result = await with_reasoning_node("wrapped_node", node)({})
        finally:
            reset_reasoning_buffer(token)

        assert result == {"done": True}
        assert buf.envelopes()[0].node == "wrapped_node"
        assert buf.envelopes()[0].steps[0].content == "Wrapped node step"

    @pytest.mark.asyncio
    async def test_reasoning_header_persists_in_envelope(self) -> None:
        async def node(_state: dict) -> dict:
            set_header("Header text")
            add_step("Step", status="completed")
            return {"ok": True}

        buf = ReasoningBuffer(thread_id="t1", anchor_message_id="m-0", sequence_base=0)
        token = set_reasoning_buffer(buf)
        try:
            result = await with_reasoning_node("header_node", node)({})
        finally:
            reset_reasoning_buffer(token)

        assert result == {"ok": True}
        assert buf.envelopes()[0].header == "Header text"

    @pytest.mark.asyncio
    async def test_with_step_marks_long_running_call_completed(self) -> None:
        async def call() -> str:
            return "ok"

        buf = ReasoningBuffer(thread_id="t1", anchor_message_id="m-0", sequence_base=0)
        token = set_reasoning_buffer(buf)
        try:
            result = await with_reasoning_node("tool_node", lambda: with_step("Calling tool", call))()
        finally:
            reset_reasoning_buffer(token)

        assert result == "ok"
        step = buf.envelopes()[0].steps[0]
        assert buf.envelopes()[0].node == "tool_node"
        assert step.content == "Calling tool"
        assert step.status == "completed"

    @pytest.mark.asyncio
    async def test_with_step_marks_long_running_call_failed(self) -> None:
        async def call() -> str:
            raise RuntimeError("boom")

        buf = ReasoningBuffer(thread_id="t1", anchor_message_id="m-0", sequence_base=0)
        token = set_reasoning_buffer(buf)
        try:
            with pytest.raises(RuntimeError):
                await with_reasoning_node("tool_node", lambda: with_step("Calling tool", call))()
        finally:
            reset_reasoning_buffer(token)

        step = buf.envelopes()[0].steps[0]
        assert buf.envelopes()[0].node == "tool_node"
        assert step.content == "Calling tool"
        assert step.status == "failed"

    def test_sse_event_json(self) -> None:
        evt = _sse_event({"category": "data", "thread_id": "t1", "messages": []})
        assert "data" in evt
        payload = json.loads(evt["data"])
        assert payload["category"] == "data"
        assert payload["thread_id"] == "t1"

    def test_node_status_map_covers_supervisor_and_inner_nodes(self) -> None:
        """Graph progress / LangGraph updates require a mapping for every user-visible graph node."""
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

    def test_openapi_blueprint_sse_categories_exclude_legacy_status(self) -> None:
        schema = app.openapi()
        mapping = schema["components"]["schemas"]["BlueprintSseEvent"]["discriminator"]["mapping"]
        assert set(mapping.keys()) == {"thinking", "data", "interrupt", "error"}
