"""Blueprints orchestration service.

Mediates between the HTTP API layer and the Blueprints LangGraph supervisor.
Controllers should call this service rather than invoking the graph directly.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.types import Command

from agents.blueprints.graph import BlueprintsGraph
from agents.blueprints.models import HumanResponse
from api.schemas.response import (
    ActionRequestDto,
    HumanInterruptConfigDto,
    InterruptDto,
    InterruptResponseDto,
    ThreadItemDto,
    ThreadResponseDto,
)
from api.schemas.thread import ResumeInputDto, ThreadMessageInputDto
from infrastructure.checkpoint.document_checkpointer import get_checkpointer
from shared.config import Settings
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


class BlueprintsService:
    """Service that orchestrates the Blueprints agent graph.

    Lifecycle:
        - Instantiated once per application (singleton via FastAPI dependency).
        - Holds a pre-compiled LangGraph instance.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._graph = BlueprintsGraph(settings)
        self._checkpointer = get_checkpointer()

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
        """
        await self._assert_thread_exists(thread_id)
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

    async def get_thread(self, thread_id: str) -> ThreadResponseDto:
        """Get the current state and messages of a thread."""
        config = {"configurable": {"thread_id": thread_id}}
        state = await self._graph.aget_state(config)

        if not state or not state.values:
            raise ResourceNotFoundError(f"Thread {thread_id} not found")

        return ThreadResponseDto(
            id=thread_id,
            messages=_format_messages(state.values),
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
