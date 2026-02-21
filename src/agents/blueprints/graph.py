"""Blueprints LangGraph — the main StateGraph wiring.

Compiles a reusable graph from:
  retrieve → generate → END

The graph is constructed once per application lifecycle (via BlueprintsGraph)
and exposes simple async methods for the application service layer.
"""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncGenerator
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langgraph.graph import END, StateGraph

from agents.blueprints.nodes import generate_template_node, retrieve_related_entities_node
from agents.blueprints.prompts import STREAMING_GENERATION_PROMPT, STREAMING_SYSTEM_PROMPT
from agents.blueprints.state import BlueprintsState
from agents.blueprints.tools.vector_search import set_store
from api.schemas.response import TemplateResponse
from api.schemas.streaming import StreamEvent, StreamEventType, StreamingTemplateResponse
from infrastructure.llm import create_embeddings, create_llm
from shared.config import Settings
from shared.exceptions import TemplateParsingError
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
        workflow.add_node("retrieve", retrieve_related_entities_node)
        workflow.add_node("generate", generate_template_node)
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
            "_llm": self._llm,
            "_vector_store": self._vector_store,
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

        accumulated_content = ""
        current_mode = StreamEventType.CONTENT

        try:
            from openai import APIConnectionError, APIError, RateLimitError

            async for chunk in self._streaming_llm.astream(messages):
                chunk_content = chunk.content if hasattr(chunk, "content") else ""
                if not chunk_content:
                    continue

                is_thinking = self._is_thinking_chunk(chunk)
                if is_thinking:
                    current_mode = StreamEventType.THINKING
                elif current_mode == StreamEventType.THINKING:
                    current_mode = StreamEventType.CONTENT

                accumulated_content += chunk_content
                yield StreamEvent(event_type=current_mode, data=chunk_content)

            # Parse and yield final template
            template_response = self._parse_streaming_response(accumulated_content)
            yield StreamEvent(
                event_type=StreamEventType.TEMPLATE,
                data=template_response.model_dump(mode="json"),
            )
            yield StreamEvent(event_type=StreamEventType.DONE, data="Stream completed")

        except (APIConnectionError, APIError, RateLimitError):
            logger.exception("LLM provider error during streaming")
            yield StreamEvent(event_type=StreamEventType.ERROR, data="Unable to communicate with AI provider")
        except (TemplateParsingError, Exception):
            logger.exception("Error during streaming generation")
            yield StreamEvent(event_type=StreamEventType.ERROR, data="Streaming generation failed")

    def _is_thinking_chunk(self, chunk: Any) -> bool:
        """Detect thinking/reasoning chunks (model-specific metadata)."""
        if hasattr(chunk, "response_metadata"):
            meta = chunk.response_metadata or {}
            if meta.get("thinking") or meta.get("reasoning"):
                return True
        if hasattr(chunk, "additional_kwargs"):
            kwargs = chunk.additional_kwargs or {}
            if kwargs.get("thinking") or kwargs.get("is_thinking"):
                return True
        return False

    def _parse_streaming_response(self, content: str) -> StreamingTemplateResponse:
        """Parse accumulated streaming content into a StreamingTemplateResponse."""
        try:
            json_match = re.search(r"```json\s*([\s\S]*?)\s*```", content)
            if json_match:
                template = TemplateResponse.model_validate(json.loads(json_match.group(1).strip()))
            else:
                template = _parser.parse(content)

            explanation_match = re.search(r"EXPLANATION:\s*([\s\S]*?)(?:\Z|```)", content, re.IGNORECASE)
            explanation = (
                explanation_match.group(1).strip()
                if explanation_match
                else "Template generated based on the provided requirements."
            )
            return StreamingTemplateResponse(template=template, explanation=explanation)
        except Exception as exc:
            raise TemplateParsingError("Unable to parse the generated template response") from exc

    def get_context_entities(self) -> list[dict[str, Any]]:
        """Return entities created in this session."""
        return list(self._context_entities)

    def clear_context(self) -> None:
        """Clear session context."""
        self._context_entities.clear()
