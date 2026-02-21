"""LangGraph state definition for the Blueprints agent.

The state is a TypedDict that flows through every node in the graph.
Each node receives the full state and returns a partial update.
"""

from __future__ import annotations

from typing import Annotated, Any

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from api.schemas.response import TemplateResponse


class BlueprintsState(TypedDict):
    """State that flows through the Blueprints LangGraph.

    Attributes:
        prompt: The original user prompt.
        messages: LangChain message history (reducer: add_messages).
        related_entities: Entities retrieved from the metadata vector store.
        context_entities: Entities added to context during this session.
        template_response: The final generated template (None until generated).
        error: Error message if a node fails (None on success).
        stream_chunks: Accumulated streaming text chunks.
    """

    prompt: str
    messages: Annotated[list[BaseMessage], add_messages]
    related_entities: list[dict[str, Any]]
    context_entities: list[dict[str, Any]]
    template_response: TemplateResponse | None
    error: str | None
    stream_chunks: list[str]
