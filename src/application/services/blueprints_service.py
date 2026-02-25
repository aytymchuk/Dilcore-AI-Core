"""Blueprints orchestration service.

Mediates between the HTTP API layer and the Blueprints LangGraph supervisor.
Controllers should call this service rather than invoking the graph directly.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from langchain_core.messages import HumanMessage

from agents.blueprints.graph import BlueprintsGraph
from api.schemas.response import ThreadItemDto, ThreadResponseDto
from api.schemas.thread import ThreadMessageInputDto
from infrastructure.checkpoint.document_checkpointer import get_checkpointer
from shared.config import Settings
from shared.exceptions import ResourceNotFoundError

logger = logging.getLogger(__name__)


def _extract_message_fields(msg: Any) -> tuple[str | None, str | None]:
    """Extract type and content from a message, handling both objects and dicts."""
    if isinstance(msg, dict):
        return msg.get("type"), msg.get("content")
    return getattr(msg, "type", None), getattr(msg, "content", None)


class BlueprintsService:
    """Service that orchestrates the Blueprints agent graph.

    Lifecycle:
        - Instantiated once per application (singleton via FastAPI dependency).
        - Holds a pre-compiled LangGraph instance.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialise with application settings.

        Args:
            settings: Application settings (LLM, vector store, etc.).
        """
        self._settings = settings
        self._graph = BlueprintsGraph(settings)
        self._checkpointer = get_checkpointer()

    async def start(self, request: ThreadMessageInputDto) -> ThreadResponseDto:
        """Start a new thread with an initial message."""
        thread_id = str(uuid.uuid4())
        return await self._process_message(thread_id, request)

    async def continue_thread(self, thread_id: str, request: ThreadMessageInputDto) -> ThreadResponseDto:
        """Continue an existing thread with a new message."""
        await self._assert_thread_exists(thread_id)
        return await self._process_message(thread_id, request)

    async def resume(self, thread_id: str, request: ThreadMessageInputDto) -> ThreadResponseDto:
        """Resume a thread flow (conceptually similar to continue_thread here)."""
        await self._assert_thread_exists(thread_id)
        return await self._process_message(thread_id, request)

    async def get_thread(self, thread_id: str) -> ThreadResponseDto:
        """Get the current state and messages of a thread."""
        config = {"configurable": {"thread_id": thread_id}}
        state_tuple = await self._checkpointer.aget_tuple(config)

        if not state_tuple:
            raise ResourceNotFoundError(f"Thread {thread_id} not found")

        messages = []
        if state_tuple.checkpoint and "channel_values" in state_tuple.checkpoint:
            channel_values = state_tuple.checkpoint["channel_values"]
            for m in channel_values.get("messages", []):
                msg_type, content = _extract_message_fields(m)
                if msg_type == "ai" and not content:
                    continue
                if msg_type and content is not None:
                    messages.append({"type": msg_type, "content": content})

        return ThreadResponseDto(id=thread_id, messages=messages)

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
                    _, first_content = _extract_message_fields(raw_messages[0])
                    if first_content:
                        name = (first_content[:30] + "...") if len(first_content) > 30 else first_content

            threads.append(ThreadItemDto(id=thread_id, name=name))

        return threads

    async def _assert_thread_exists(self, thread_id: str) -> None:
        """Raise ResourceNotFoundError if no checkpoint exists for thread_id."""
        config = {"configurable": {"thread_id": thread_id}}
        if not await self._checkpointer.aget_tuple(config):
            raise ResourceNotFoundError(f"Thread {thread_id} not found")

    async def _process_message(self, thread_id: str, request: ThreadMessageInputDto) -> ThreadResponseDto:
        """Internal helper to invoke the supervisor with a configurable thread_id."""
        config = {"configurable": {"thread_id": thread_id}}
        state_input = {"messages": [HumanMessage(content=request.message)]}

        result = await self._graph.ainvoke(state_input, config=config)

        message_dicts = []
        for m in result.get("messages", []):
            msg_type, content = _extract_message_fields(m)
            if msg_type == "ai" and not content:
                continue
            if msg_type and content is not None:
                message_dicts.append({"type": msg_type, "content": content})

        return ThreadResponseDto(id=thread_id, messages=message_dicts)
