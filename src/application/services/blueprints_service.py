"""Blueprints orchestration service.

Mediates between the HTTP API layer and the Blueprints LangGraph supervisor.
Controllers should call this service rather than invoking the graph directly.
"""

from __future__ import annotations

import logging
import uuid

from langchain_core.messages import HumanMessage

from agents.blueprints.graph import BlueprintsGraph
from api.schemas.response import ThreadItemDto, ThreadResponseDto
from api.schemas.thread import ThreadMessageInputDto
from infrastructure.checkpoint.document_checkpointer import get_checkpointer
from shared.config import Settings

logger = logging.getLogger(__name__)


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
        # We access the singleton checkpointer, required to list state for existing threads
        self._checkpointer = get_checkpointer()

    async def start(self, request: ThreadMessageInputDto) -> ThreadResponseDto:
        """Start a new thread with an initial message."""
        thread_id = str(uuid.uuid4())
        return await self._process_message(thread_id, request)

    async def continue_thread(self, thread_id: str, request: ThreadMessageInputDto) -> ThreadResponseDto:
        """Continue an existing thread with a new message."""
        return await self._process_message(thread_id, request)

    async def resume(self, thread_id: str, request: ThreadMessageInputDto) -> ThreadResponseDto:
        """Resume a thread flow (conceptually similar to continue_thread here)."""
        # E.g. If the graph was fully interrupted and waiting for user feedback,
        # we can pass the message back.
        return await self._process_message(thread_id, request)

    async def get_thread(self, thread_id: str) -> ThreadResponseDto:
        """Get the current state and messages of a thread."""
        config = {"configurable": {"thread_id": thread_id}}
        state_tuple = self._checkpointer.get_tuple(config)

        messages = []
        if state_tuple and state_tuple.checkpoint and "channel_values" in state_tuple.checkpoint:
            channel_values = state_tuple.checkpoint["channel_values"]
            if "messages" in channel_values:
                for m in channel_values["messages"]:
                    if m.type == "ai" and (m.content == "" or m.content is None):
                        continue
                    messages.append({"type": m.type, "content": m.content})

        return ThreadResponseDto(id=thread_id, messages=messages)

    async def get_threads(self) -> list[ThreadItemDto]:
        """List all tracked threads."""
        threads = []
        # LangGraph MongoDB checkpointer allows listing all state checkpoints.
        # This implementation depends on how `MemorySaver.list()` exposes data.
        # We group by thread_id to ensure we only get the latest state per thread.
        seen_threads = set()
        for state_tuple in self._checkpointer.list({"configurable": {}}):
            thread_id = state_tuple.config["configurable"]["thread_id"]
            if thread_id not in seen_threads:
                seen_threads.add(thread_id)

                # Derive a name from the first message
                name = f"Thread {thread_id[:8]}"
                if state_tuple.checkpoint and "channel_values" in state_tuple.checkpoint:
                    channel_values = state_tuple.checkpoint["channel_values"]
                    if "messages" in channel_values and len(channel_values["messages"]) > 0:
                        first_msg = channel_values["messages"][0]
                        name = (first_msg.content[:30] + "...") if len(first_msg.content) > 30 else first_msg.content

                threads.append(ThreadItemDto(id=thread_id, name=name))

        return threads

    async def _process_message(self, thread_id: str, request: ThreadMessageInputDto) -> ThreadResponseDto:
        """Internal helper to invoke the supervisor with a configurable thread_id."""
        config = {"configurable": {"thread_id": thread_id}}

        # The supervisor graph will route the message to the appropriate sub-graph.
        # We pass the user message as a HumanMessage dict to the state.
        state_input = {"messages": [HumanMessage(content=request.message)]}

        # Since the supervisor is stateless but wraps a sub-graph that DOES have a checkpointer
        # calling it with config will cause the sub-graph to load state if routed there.
        # However, because the Supervisor isn't stateful, it won't persist its own state.
        result = await self._graph.ainvoke(state_input, config=config)

        # Format output messages for the DTO.
        # Skip AI messages with empty content (tool-call placeholders from ReAct).
        message_dicts = []
        if "messages" in result:
            for m in result["messages"]:
                if m.type == "ai" and not m.content:
                    continue
                message_dicts.append({"type": m.type, "content": m.content})

        return ThreadResponseDto(id=thread_id, messages=message_dicts)
