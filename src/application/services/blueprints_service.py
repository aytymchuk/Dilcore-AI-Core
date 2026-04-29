"""Blueprints orchestration service.

Mediates between the HTTP API layer and the Blueprints LangGraph supervisor.
Controllers should call this service rather than invoking the graph directly.
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agents.blueprints.graph import BlueprintsGraph
from agents.blueprints.models import HumanResponse
from agents.blueprints.runtime import BlueprintsRuntime
from api.schemas.response import (
    ActionRequestDto,
    HumanInterruptConfigDto,
    InterruptDto,
    InterruptResponseDto,
    ThreadItemDto,
    ThreadResponseDto,
)
from api.schemas.thread import ResumeInputDto, ThreadMessageInputDto
from shared.exceptions import ResourceNotFoundError
from shared.reasoning import (
    ReasoningBuffer,
    SupervisorStructuredCaptureState,
    consume_supervisor_structured_delta,
    extract_agent_type,
    extract_reasoning_delta,
    extract_text_delta,
    reset_reasoning_buffer,
    serialize_reasoning_envelopes,
    set_reasoning_buffer,
)

logger = logging.getLogger(__name__)


def _extract_message_fields(msg: Any) -> tuple[str | None, str | None, str | None]:
    """Extract type, content, and agent_type from a message.

    Handles both LangChain BaseMessage objects and plain dicts.
    The agent_type is stored in ``additional_kwargs["agent_type"]``.
    """
    if isinstance(msg, dict):
        agent_type = (msg.get("additional_kwargs") or {}).get("agent_type")
        return msg.get("type"), msg.get("content"), agent_type
    kwargs = getattr(msg, "additional_kwargs", None) or {}
    return (
        getattr(msg, "type", None),
        getattr(msg, "content", None),
        kwargs.get("agent_type"),
    )


def _format_messages(result: dict) -> list[dict]:
    """Extract displayable messages from a graph result, filtering empty AI placeholders."""
    message_dicts = []
    for m in result.get("messages", []):
        msg_type, content, agent_type = _extract_message_fields(m)
        if msg_type == "ai" and not content:
            continue
        if msg_type and content is not None:
            message_dicts.append(
                {
                    "id": f"m-{len(message_dicts)}",
                    "type": msg_type,
                    "content": content,
                    "agent_type": agent_type,
                }
            )
    return message_dicts


def _build_human_response(request: ResumeInputDto) -> HumanResponse:
    """Normalise a ``ResumeInputDto`` into a ``HumanResponse`` dict.

    Plain-text ``message`` is promoted to ``type="response"``.
    """
    if request.type is not None:
        args: Any = request.args
        if isinstance(args, ActionRequestDto):
            args = {"action": args.action, "args": args.args}
        return HumanResponse(type=request.type, args=args)

    return HumanResponse(type="response", args=request.message)


def _extract_interrupts(state: Any) -> list[InterruptDto]:
    """Pull pending ``HumanInterrupt`` dicts out of a ``StateSnapshot``."""
    if not state or not state.tasks:
        return []

    dtos: list[InterruptDto] = []
    for task in state.tasks:
        for intr in task.interrupts:
            for item in intr.value if isinstance(intr.value, list) else [intr.value]:
                if not isinstance(item, dict):
                    continue
                ar = item.get("action_request", {})
                cfg = item.get("config", {})
                dtos.append(
                    InterruptDto(
                        action_request=ActionRequestDto(
                            action=ar.get("action", ""),
                            args=ar.get("args", {}),
                        ),
                        config=HumanInterruptConfigDto(
                            allow_ignore=cfg.get("allow_ignore", False),
                            allow_respond=cfg.get("allow_respond", True),
                            allow_edit=cfg.get("allow_edit", False),
                            allow_accept=cfg.get("allow_accept", True),
                        ),
                        description=item.get("description"),
                    )
                )
    return dtos


def _sse_event(payload: dict[str, Any]) -> dict[str, str]:
    """Shape a single SSE payload for :class:`sse_starlette.sse.EventSourceResponse`."""
    return {"data": json.dumps(payload, default=str)}


def _parse_langgraph_stream_chunk(chunk: Any) -> tuple[str, Any] | None:
    """Normalize LangGraph stream items (tuple or v2 dict) to ``(mode, data)``."""
    if isinstance(chunk, dict) and "type" in chunk:
        return str(chunk["type"]), chunk["data"]
    if isinstance(chunk, tuple) and len(chunk) == 2:
        return str(chunk[0]), chunk[1]
    return None


def _langgraph_node_from_stream_metadata(metadata: Any) -> str | None:
    """Best-effort graph node name from LangGraph ``messages`` stream metadata."""
    if not isinstance(metadata, dict):
        return None
    node = metadata.get("langgraph_node")
    return node if isinstance(node, str) and node else None


# LangGraph node name -> (user-facing status message, coarse phase for UI grouping)
_NODE_STATUS_MAP: dict[str, tuple[str, str]] = {
    "supervisor": ("Analyzing your request...", "routing"),
    "ask": ("Answering your question...", "ask"),
    "design": ("Working on the design...", "design"),
    "generate": ("Preparing generation...", "generate"),
    "identify_intent": ("Clarifying your request...", "identify_intent"),
    "build_plan": ("Building generation plan...", "generate"),
    "present_plan": ("Presenting plan for review...", "generate"),
    "collect_response": ("Awaiting plan confirmation...", "generate"),
    "handle_response": ("Processing your feedback...", "generate"),
    "write_success": ("Executing generation plan...", "generate"),
    "ask_agent": ("Answering your question...", "ask"),
    "design_agent": ("Working on the design...", "design"),
    "update_design_context": ("Updating design context...", "design"),
}

# Nodes we expect to appear in stream updates (supervisor graph + inner nodes); used by tests.
EXPECTED_STREAM_STATUS_NODES: frozenset[str] = frozenset(_NODE_STATUS_MAP.keys())


def _graph_progress_thinking_sse(buffer: ReasoningBuffer, node_name: str) -> dict[str, Any] | None:
    """Map a completed LangGraph ``updates`` node key to a persisted reasoning step + SSE payload."""
    mapped = _NODE_STATUS_MAP.get(node_name)
    if mapped is None:
        return None
    message, phase = mapped
    env = buffer.add_step(message, status="completed", node=node_name)
    return {
        "category": "thinking",
        "type": "reasoning",
        "content": message,
        "kind": "step",
        "status": "completed",
        "phase": phase,
        "after_message_id": env.after_message_id,
        "sequence": env.sequence,
        "node": node_name,
    }


def _stream_run_config(thread_id: str) -> dict[str, Any]:
    return {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 100,
    }


class BlueprintsService:
    """Service that orchestrates the Blueprints agent graph.

    Lifecycle:
        - Instantiated once per application (singleton via FastAPI dependency).
        - Holds a pre-compiled LangGraph instance.
    """

    def __init__(self, runtime: BlueprintsRuntime) -> None:
        self._graph = BlueprintsGraph(runtime)
        self._checkpointer = runtime.checkpointer

    async def start(self, request: ThreadMessageInputDto) -> ThreadResponseDto | InterruptResponseDto:
        """Start a new thread with an initial message."""
        thread_id = str(uuid.uuid4())
        return await self._invoke_graph(thread_id, request)

    async def continue_thread(
        self,
        thread_id: str,
        request: ThreadMessageInputDto,
    ) -> ThreadResponseDto | InterruptResponseDto:
        """Continue an existing thread with a new message.

        Always starts from the supervisor so the user's new intent is re-evaluated.
        If an interrupt is pending, requires the user to /resume instead.
        """
        await self._assert_thread_exists(thread_id)

        config = {"configurable": {"thread_id": thread_id}}
        state = await self._graph.aget_state(config)

        interrupts = _extract_interrupts(state)
        if interrupts:
            # Graph is paused at an interrupt. Force user to resume.
            return InterruptResponseDto(
                id=thread_id,
                interrupts=interrupts,
                messages=_format_messages(state.values) if state else [],
            )

        return await self._invoke_graph(thread_id, request)

    async def resume(
        self,
        thread_id: str,
        request: ResumeInputDto,
    ) -> ThreadResponseDto | InterruptResponseDto:
        """Resume a thread that was paused by a graph interrupt.

        Accepts either a structured ``ResumeInputDto`` (with explicit type)
        or a plain-text message fallback.  Both are normalised into a
        ``HumanResponse`` dict before being passed to ``Command(resume=...)``.
        """
        await self._assert_thread_exists(thread_id)
        config = {"configurable": {"thread_id": thread_id}}

        state = await self._graph.aget_state(config)
        if not state or not state.next:
            raise ResourceNotFoundError(f"Thread {thread_id} has no pending interrupt to resume")

        resume_value = _build_human_response(request)
        # Ensure fluent reasoning API is available during non-stream runs too.
        existing_messages = _format_messages(state.values) if state and isinstance(state.values, dict) else []
        base_count = len(existing_messages)
        existing_reasoning = (
            (state.values or {}).get("reasoning", []) if state and isinstance(state.values, dict) else []
        )
        max_seq = max((x.get("sequence", 0) for x in existing_reasoning if isinstance(x, dict)), default=0)
        buffer = ReasoningBuffer(thread_id=thread_id, anchor_message_id=f"m-{base_count}", sequence_base=max_seq)
        token = set_reasoning_buffer(buffer)
        try:
            result = await self._graph.ainvoke(
                Command(resume=resume_value),
                config=config,
            )
            await self._persist_reasoning_envelopes(config, buffer)
        finally:
            reset_reasoning_buffer(token)
        return await self._build_response(thread_id, config, result)

    async def get_thread(self, thread_id: str) -> ThreadResponseDto | InterruptResponseDto:
        """Get the current state and messages of a thread."""
        logger.info("Attempting to retrieve thread %s", thread_id)
        config = {"configurable": {"thread_id": thread_id}}
        state = await self._graph.aget_state(config)

        if not state or not state.values:
            logger.warning("Thread %s not found in checkpoint store", thread_id)
            raise ResourceNotFoundError(f"Thread {thread_id} not found")

        logger.info("Successfully retrieved thread %s", thread_id)
        messages = _format_messages(state.values)
        reasoning = (state.values or {}).get("reasoning", []) if isinstance(state.values, dict) else []
        interrupts = _extract_interrupts(state)

        if interrupts:
            return InterruptResponseDto(
                id=thread_id,
                interrupts=interrupts,
                messages=messages,
                reasoning=reasoning,
            )

        return ThreadResponseDto(id=thread_id, messages=messages, reasoning=reasoning)

    async def start_stream(
        self,
        request: ThreadMessageInputDto,
    ) -> AsyncIterator[dict[str, str]]:
        """Stream graph execution for a new thread over SSE (see JSON ``category`` field)."""
        thread_id = str(uuid.uuid4())
        config = _stream_run_config(thread_id)
        state_input: dict[str, Any] = {"messages": [HumanMessage(content=request.message)]}
        buffer = ReasoningBuffer(thread_id=thread_id, anchor_message_id="m-0", sequence_base=0)
        token = set_reasoning_buffer(buffer)
        try:
            async for event in self._stream_graph_execution(state_input, config, buffer, base_message_count=0):
                yield event
            await self._persist_reasoning_envelopes(config, buffer)
            async for event in self._stream_final_payload(thread_id, config):
                yield event
        except Exception as e:  # noqa: BLE001 — surfaced to client as SSE error
            logger.exception("Blueprints start_stream failed for thread %s", thread_id)
            try:
                await self._persist_reasoning_envelopes(config, buffer, streaming_success=False)
            except Exception:  # noqa: BLE001
                logger.exception("Blueprints start_stream failed to persist reasoning after error")
            yield _sse_event({"category": "error", "detail": str(e)})
        finally:
            reset_reasoning_buffer(token)

    async def continue_stream(
        self,
        thread_id: str,
        request: ThreadMessageInputDto,
    ) -> AsyncIterator[dict[str, str]]:
        """Stream graph execution when continuing a thread (supervisor re-entry)."""
        try:
            await self._assert_thread_exists(thread_id)
        except ResourceNotFoundError as e:
            yield _sse_event({"category": "error", "detail": str(e)})
            return

        config = _stream_run_config(thread_id)
        state = await self._graph.aget_state(config)
        interrupts = _extract_interrupts(state)
        if interrupts:
            yield _sse_event(
                {
                    "category": "interrupt",
                    "id": thread_id,
                    "interrupts": [i.model_dump(mode="json") for i in interrupts],
                    "messages": _format_messages(state.values) if state else [],
                    "reasoning": (state.values or {}).get("reasoning", [])
                    if state and isinstance(state.values, dict)
                    else [],
                }
            )
            return

        state_input: dict[str, Any] = {"messages": [HumanMessage(content=request.message)]}
        existing_messages = _format_messages(state.values) if state and isinstance(state.values, dict) else []
        base_count = len(existing_messages)
        existing_reasoning = (
            (state.values or {}).get("reasoning", []) if state and isinstance(state.values, dict) else []
        )
        max_seq = max((x.get("sequence", 0) for x in existing_reasoning if isinstance(x, dict)), default=0)
        buffer = ReasoningBuffer(thread_id=thread_id, anchor_message_id=f"m-{base_count}", sequence_base=max_seq)
        token = set_reasoning_buffer(buffer)
        try:
            async for event in self._stream_graph_execution(state_input, config, buffer, base_message_count=base_count):
                yield event
            await self._persist_reasoning_envelopes(config, buffer)
            async for event in self._stream_final_payload(thread_id, config):
                yield event
        except Exception as e:  # noqa: BLE001
            logger.exception("Blueprints continue_stream failed for thread %s", thread_id)
            try:
                await self._persist_reasoning_envelopes(config, buffer, streaming_success=False)
            except Exception:  # noqa: BLE001
                logger.exception("Blueprints continue_stream failed to persist reasoning after error")
            yield _sse_event({"category": "error", "detail": str(e)})
        finally:
            reset_reasoning_buffer(token)

    async def resume_stream(
        self,
        thread_id: str,
        request: ResumeInputDto,
    ) -> AsyncIterator[dict[str, str]]:
        """Stream graph execution when resuming from a human-in-the-loop interrupt."""
        try:
            await self._assert_thread_exists(thread_id)
        except ResourceNotFoundError as e:
            yield _sse_event({"category": "error", "detail": str(e)})
            return

        config = _stream_run_config(thread_id)
        state = await self._graph.aget_state(config)
        if not state or not state.next:
            yield _sse_event(
                {
                    "category": "error",
                    "detail": f"Thread {thread_id} has no pending interrupt to resume",
                }
            )
            return

        resume_value = _build_human_response(request)
        command_input = Command(resume=resume_value)
        existing_messages = _format_messages(state.values) if state and isinstance(state.values, dict) else []
        base_count = len(existing_messages)
        existing_reasoning = (
            (state.values or {}).get("reasoning", []) if state and isinstance(state.values, dict) else []
        )
        max_seq = max((x.get("sequence", 0) for x in existing_reasoning if isinstance(x, dict)), default=0)
        buffer = ReasoningBuffer(thread_id=thread_id, anchor_message_id=f"m-{base_count}", sequence_base=max_seq)
        token = set_reasoning_buffer(buffer)
        try:
            async for event in self._stream_graph_execution(
                command_input, config, buffer, base_message_count=base_count
            ):
                yield event
            await self._persist_reasoning_envelopes(config, buffer)
            async for event in self._stream_final_payload(thread_id, config):
                yield event
        except Exception as e:  # noqa: BLE001
            logger.exception("Blueprints resume_stream failed for thread %s", thread_id)
            try:
                await self._persist_reasoning_envelopes(config, buffer, streaming_success=False)
            except Exception:  # noqa: BLE001
                logger.exception("Blueprints resume_stream failed to persist reasoning after error")
            yield _sse_event({"category": "error", "detail": str(e)})
        finally:
            reset_reasoning_buffer(token)

    async def _stream_graph_execution(
        self,
        graph_input: Any,
        config: dict[str, Any],
        buffer: ReasoningBuffer,
        *,
        base_message_count: int,
    ) -> AsyncIterator[dict[str, str]]:
        """Map LangGraph stream chunks to semantic SSE JSON events (``category`` field)."""
        assistant_anchor_set = False
        route_capture = SupervisorStructuredCaptureState()
        async for chunk in self._graph.astream(
            graph_input,
            config=config,
            stream_mode=["messages", "updates"],
        ):
            parsed = _parse_langgraph_stream_chunk(chunk)
            if not parsed:
                continue
            mode, data = parsed
            if mode == "messages":
                msg_chunk, stream_metadata = data
                stream_node = _langgraph_node_from_stream_metadata(stream_metadata)
                reasoning = extract_reasoning_delta(msg_chunk)
                if reasoning:
                    r_type, r_text = reasoning
                    agent_type = extract_agent_type(msg_chunk)
                    env = buffer.add_provider_delta(r_type, r_text, agent_type=agent_type)
                    yield _sse_event(
                        {
                            "category": "thinking",
                            "type": r_type,
                            "content": r_text,
                            "kind": "step",
                            "status": "running",
                            "after_message_id": env.after_message_id,
                            "sequence": env.sequence,
                            "agent_type": agent_type,
                        }
                    )

                text = extract_text_delta(msg_chunk)
                if text:
                    agent_type_msg = extract_agent_type(msg_chunk)
                    emit_text, struct_effects = consume_supervisor_structured_delta(
                        route_capture,
                        text,
                        agent_type=agent_type_msg,
                    )
                    for eff in struct_effects:
                        if eff["kind"] == "supervisor_stream_start":
                            yield _sse_event(
                                {
                                    "category": "thinking",
                                    "type": "reasoning",
                                    "content": "Receiving structured routing decision…",
                                    "kind": "step",
                                    "status": "running",
                                    "node": "supervisor",
                                    "after_message_id": buffer.anchor_message_id,
                                }
                            )
                        elif eff["kind"] == "supervisor_stream_parsed":
                            env = buffer.add_step(
                                f"Structured routing complete → next_route={eff['next_route']}",
                                status="completed",
                                node="supervisor",
                            )
                            yield _sse_event(
                                {
                                    "category": "thinking",
                                    "type": "reasoning",
                                    "content": eff["reasoning"],
                                    "kind": "step",
                                    "status": "completed",
                                    "after_message_id": env.after_message_id,
                                    "sequence": env.sequence,
                                    "node": "supervisor",
                                }
                            )
                    if emit_text:
                        if not assistant_anchor_set:
                            buffer.close_on_text_delta(new_anchor_message_id=f"m-{base_message_count + 1}")
                            assistant_anchor_set = True
                        env_reply = buffer.add_assistant_reply_delta(
                            emit_text,
                            agent_type=agent_type_msg,
                            node=stream_node,
                        )
                        yield _sse_event(
                            {
                                "category": "thinking",
                                "type": "reasoning",
                                "content": emit_text,
                                "kind": "step",
                                "status": "running",
                                "after_message_id": env_reply.after_message_id,
                                "sequence": env_reply.sequence,
                                "agent_type": agent_type_msg,
                                "node": stream_node,
                            }
                        )
            elif mode == "updates" and isinstance(data, dict):
                for node_name in data:
                    payload = _graph_progress_thinking_sse(buffer, node_name)
                    if payload is not None:
                        yield _sse_event(payload)

    async def _persist_reasoning_envelopes(
        self,
        config: dict[str, Any],
        buffer: ReasoningBuffer,
        *,
        streaming_success: bool = True,
    ) -> None:
        buffer.finalize_streaming_steps(success=streaming_success)
        envelopes = buffer.envelopes()
        if not envelopes:
            return
        await self._graph.aupdate_state(config, {"reasoning": serialize_reasoning_envelopes(envelopes)})

    async def _stream_final_payload(
        self,
        thread_id: str,
        config: dict[str, Any],
    ) -> AsyncIterator[dict[str, str]]:
        """Emit terminal ``interrupt`` or ``data`` event from checkpoint state."""
        state = await self._graph.aget_state(config)
        values = state.values if state else {}
        interrupts = _extract_interrupts(state)
        messages = _format_messages(values if isinstance(values, dict) else {})
        reasoning = values.get("reasoning", []) if isinstance(values, dict) else []

        if interrupts:
            yield _sse_event(
                {
                    "category": "interrupt",
                    "id": thread_id,
                    "interrupts": [i.model_dump(mode="json") for i in interrupts],
                    "messages": messages,
                    "reasoning": reasoning,
                }
            )
        else:
            yield _sse_event(
                {
                    "category": "data",
                    "thread_id": thread_id,
                    "messages": messages,
                    "reasoning": reasoning,
                }
            )

    async def get_threads(self) -> list[ThreadItemDto]:
        """List all tracked threads."""
        threads = []
        seen_threads: set[str] = set()
        async for state_tuple in self._checkpointer.alist({"configurable": {}}):
            thread_id = state_tuple.config["configurable"]["thread_id"]
            if thread_id in seen_threads:
                continue
            seen_threads.add(thread_id)

            name = f"Thread {thread_id[:8]}"
            if state_tuple.checkpoint and "channel_values" in state_tuple.checkpoint:
                channel_values = state_tuple.checkpoint["channel_values"]
                raw_messages = channel_values.get("messages", [])
                if raw_messages:
                    _, first_content, _ = _extract_message_fields(raw_messages[0])
                    if first_content:
                        name = (first_content[:30] + "...") if len(first_content) > 30 else first_content

            threads.append(ThreadItemDto(id=thread_id, name=name))

        return threads

    async def _assert_thread_exists(self, thread_id: str) -> None:
        """Raise ResourceNotFoundError if no checkpoint exists for thread_id."""
        config = {"configurable": {"thread_id": thread_id}}
        if not await self._checkpointer.aget_tuple(config):
            raise ResourceNotFoundError(f"Thread {thread_id} not found")

    async def _invoke_graph(
        self,
        thread_id: str,
        request: ThreadMessageInputDto,
    ) -> ThreadResponseDto | InterruptResponseDto:
        """Invoke the graph from the supervisor entry point with a new user message."""
        config = {"configurable": {"thread_id": thread_id}}
        state_input = {"messages": [HumanMessage(content=request.message)]}

        # Ensure fluent reasoning API is available during non-stream runs too.
        state = await self._graph.aget_state(config)
        existing_messages = _format_messages(state.values) if state and isinstance(state.values, dict) else []
        base_count = len(existing_messages)
        existing_reasoning = (
            (state.values or {}).get("reasoning", []) if state and isinstance(state.values, dict) else []
        )
        max_seq = max((x.get("sequence", 0) for x in existing_reasoning if isinstance(x, dict)), default=0)
        buffer = ReasoningBuffer(thread_id=thread_id, anchor_message_id=f"m-{base_count}", sequence_base=max_seq)
        token = set_reasoning_buffer(buffer)
        try:
            result = await self._graph.ainvoke(state_input, config=config)
            await self._persist_reasoning_envelopes(config, buffer)
        finally:
            reset_reasoning_buffer(token)
        return await self._build_response(thread_id, config, result)

    async def _build_response(
        self,
        thread_id: str,
        config: dict,
        result: dict,
    ) -> ThreadResponseDto | InterruptResponseDto:
        """Inspect the graph state after invocation.

        If there are pending interrupts, return an ``InterruptResponseDto``;
        otherwise return a normal ``ThreadResponseDto``.
        """
        state = await self._graph.aget_state(config)
        interrupts = _extract_interrupts(state)
        reasoning = (state.values or {}).get("reasoning", []) if state and isinstance(state.values, dict) else []

        messages = _format_messages(result)

        if interrupts:
            return InterruptResponseDto(
                id=thread_id,
                interrupts=interrupts,
                messages=messages,
                reasoning=reasoning,
            )

        return ThreadResponseDto(id=thread_id, messages=messages, reasoning=reasoning)
