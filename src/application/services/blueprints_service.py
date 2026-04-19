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


def _text_token_delta_from_message_chunk(msg_chunk: Any) -> str | None:
    """Extract user-visible text deltas from a streamed message chunk (not reasoning)."""
    content = getattr(msg_chunk, "content", None)
    if content is None:
        return None
    if isinstance(content, str) and content:
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        joined = "".join(parts)
        return joined if joined else None
    return None


def _reasoning_delta_from_message_chunk(msg_chunk: Any) -> str | None:
    """Extract reasoning / extended-thinking deltas when the model exposes them."""
    rc = getattr(msg_chunk, "reasoning_content", None)
    if rc:
        return rc if isinstance(rc, str) else str(rc)
    additional = getattr(msg_chunk, "additional_kwargs", None) or {}
    nested = additional.get("reasoning_content")
    if nested:
        return nested if isinstance(nested, str) else str(nested)
    content = getattr(msg_chunk, "content", None)
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if not isinstance(block, dict):
                continue
            if block.get("type") not in ("thinking", "reasoning"):
                continue
            piece = block.get("thinking") or block.get("reasoning") or block.get("text")
            if piece:
                parts.append(str(piece))
        if parts:
            return "".join(parts)
    return None


def _agent_type_from_message_chunk(msg_chunk: Any) -> str | None:
    additional = getattr(msg_chunk, "additional_kwargs", None) or {}
    at = additional.get("agent_type")
    return str(at) if at is not None else None


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
        result = await self._graph.ainvoke(
            Command(resume=resume_value),
            config=config,
        )
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
        interrupts = _extract_interrupts(state)

        if interrupts:
            return InterruptResponseDto(
                id=thread_id,
                interrupts=interrupts,
                messages=messages,
            )

        return ThreadResponseDto(id=thread_id, messages=messages)

    async def start_stream(
        self,
        request: ThreadMessageInputDto,
    ) -> AsyncIterator[dict[str, str]]:
        """Stream graph execution for a new thread over SSE (see JSON ``category`` field)."""
        thread_id = str(uuid.uuid4())
        config = _stream_run_config(thread_id)
        state_input: dict[str, Any] = {"messages": [HumanMessage(content=request.message)]}
        try:
            async for event in self._stream_graph_execution(state_input, config):
                yield event
            async for event in self._stream_final_payload(thread_id, config):
                yield event
        except Exception as e:  # noqa: BLE001 — surfaced to client as SSE error
            logger.exception("Blueprints start_stream failed for thread %s", thread_id)
            yield _sse_event({"category": "error", "detail": str(e)})

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
                }
            )
            return

        state_input: dict[str, Any] = {"messages": [HumanMessage(content=request.message)]}
        try:
            async for event in self._stream_graph_execution(state_input, config):
                yield event
            async for event in self._stream_final_payload(thread_id, config):
                yield event
        except Exception as e:  # noqa: BLE001
            logger.exception("Blueprints continue_stream failed for thread %s", thread_id)
            yield _sse_event({"category": "error", "detail": str(e)})

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
        try:
            async for event in self._stream_graph_execution(command_input, config):
                yield event
            async for event in self._stream_final_payload(thread_id, config):
                yield event
        except Exception as e:  # noqa: BLE001
            logger.exception("Blueprints resume_stream failed for thread %s", thread_id)
            yield _sse_event({"category": "error", "detail": str(e)})

    async def _stream_graph_execution(
        self,
        graph_input: Any,
        config: dict[str, Any],
    ) -> AsyncIterator[dict[str, str]]:
        """Map LangGraph stream chunks to semantic SSE JSON events (``category`` field)."""
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
                msg_chunk, _metadata = data
                reasoning = _reasoning_delta_from_message_chunk(msg_chunk)
                if reasoning:
                    yield _sse_event({"category": "thinking", "content": reasoning})
                text = _text_token_delta_from_message_chunk(msg_chunk)
                if text:
                    yield _sse_event(
                        {
                            "category": "delta",
                            "content": text,
                            "agent_type": _agent_type_from_message_chunk(msg_chunk),
                        }
                    )
            elif mode == "updates" and isinstance(data, dict):
                for node_name in data:
                    mapped = _NODE_STATUS_MAP.get(node_name)
                    if mapped is not None:
                        message, phase = mapped
                        yield _sse_event(
                            {
                                "category": "status",
                                "message": message,
                                "phase": phase,
                            }
                        )

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

        if interrupts:
            yield _sse_event(
                {
                    "category": "interrupt",
                    "id": thread_id,
                    "interrupts": [i.model_dump(mode="json") for i in interrupts],
                    "messages": messages,
                }
            )
        else:
            yield _sse_event(
                {
                    "category": "data",
                    "thread_id": thread_id,
                    "messages": messages,
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

        result = await self._graph.ainvoke(state_input, config=config)
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

        messages = _format_messages(result)

        if interrupts:
            return InterruptResponseDto(
                id=thread_id,
                interrupts=interrupts,
                messages=messages,
            )

        return ThreadResponseDto(id=thread_id, messages=messages)
