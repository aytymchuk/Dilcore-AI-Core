"""Blueprints LangGraph — the main StateGraph wiring.

Compiles a reusable graph from:
  retrieve → generate → END

The graph is constructed once per application lifecycle (via BlueprintsGraph)
and exposes simple async methods for the application service layer.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import END, StateGraph

from agents.blueprints.nodes import GenerateTemplateNode, RetrieveRelatedEntitiesNode
from agents.blueprints.prompts import STREAMING_GENERATION_PROMPT, STREAMING_SYSTEM_PROMPT
from agents.blueprints.state import BlueprintsState
from agents.blueprints.tools.vector_search import set_store
from api.schemas.response import TemplateResponse
from api.schemas.streaming import StreamEvent
from infrastructure.llm import create_embeddings, create_llm
from shared.config import Settings, get_settings
from shared.exceptions import TemplateParsingError
from shared.streaming import StreamEmitter
from store.vector import FaissVectorStore

logger = logging.getLogger(__name__)

_parser = PydanticOutputParser(pydantic_object=TemplateResponse)


class BlueprintsGraph:
    """Encapsulates the compiled Blueprints LangGraph.

    Lifecycle:
        - Created once per application (thin wrapper around the compiled graph).
        - Holds LLM clients and vector store references.
        - Maintains a simple in-session context list (context_entities).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm = create_llm(settings, streaming=False)
        self._streaming_llm = create_llm(settings, streaming=True)
        self._embeddings = create_embeddings(settings)
        self._context_entities: list[dict[str, Any]] = []

        # Set up vector store
        self._vector_store = FaissVectorStore(
            embeddings=self._embeddings,
            index_path=settings.vector_store.metadata_index_path,
        )
        self._vector_store.load()
        set_store(self._vector_store)

        self._graph = self._build_graph()

    def _build_graph(self):
        """Build and compile the LangGraph StateGraph."""
        workflow = StateGraph(BlueprintsState)
        workflow.add_node("retrieve", RetrieveRelatedEntitiesNode(self._vector_store))
        workflow.add_node("generate", GenerateTemplateNode(self._llm))
        workflow.set_entry_point("retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_edge("generate", END)
        return workflow.compile()

    async def generate(self, prompt: str) -> TemplateResponse:
        """Run the graph to produce a TemplateResponse.

        Args:
            prompt: User's natural language prompt.

        Returns:
            Parsed TemplateResponse.
        """
        initial_state: dict[str, Any] = {
            "prompt": prompt,
            "messages": [],
            "related_entities": [],
            "context_entities": list(self._context_entities),
            "template_response": None,
            "error": None,
            "stream_chunks": [],
        }
        result = await self._graph.ainvoke(initial_state)

        if result.get("error"):
            raise TemplateParsingError(result["error"])

        template: TemplateResponse = result["template_response"]
        # Add to context for relational awareness
        self._context_entities.append({"id": template.template_id, "name": template.template_name})
        return template

    async def generate_stream(self, prompt: str) -> AsyncGenerator[StreamEvent, None]:
        """Stream template generation events using SSE-compatible chunks.

        Args:
            prompt: User's natural language prompt.

        Yields:
            StreamEvent objects.
        """
        messages = [
            SystemMessage(content=STREAMING_SYSTEM_PROMPT),
            HumanMessage(
                content=STREAMING_GENERATION_PROMPT.format(
                    prompt=prompt,
                    format_instructions=_parser.get_format_instructions(),
                )
            ),
        ]

        emitter = StreamEmitter(self._streaming_llm, messages, _parser)
        async for event in emitter.stream():
            yield event

    def get_context_entities(self) -> list[dict[str, Any]]:
        """Return entities created in this session."""
        return list(self._context_entities)

    def clear_context(self) -> None:
        """Clear session context."""
        self._context_entities.clear()


# Expose compiled StateGraph for LangGraph Studio/CLI
graph = BlueprintsGraph(get_settings())._graph
