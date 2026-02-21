"""Blueprints orchestration service.

Mediates between the HTTP API layer and the Blueprints LangGraph agent.
Controllers should call this service rather than invoking the graph directly.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any

from agents.blueprints.graph import BlueprintsGraph
from api.schemas.response import TemplateResponse
from api.schemas.streaming import StreamEvent
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

    async def generate_template(self, prompt: str) -> TemplateResponse:
        """Generate a structured metadata template.

        Args:
            prompt: Natural language description of the template to create.

        Returns:
            Parsed TemplateResponse.
        """
        logger.info("BlueprintsService: generate_template called")
        return await self._graph.generate(prompt)

    async def generate_template_stream(self, prompt: str) -> AsyncGenerator[StreamEvent, None]:
        """Stream template generation events.

        Args:
            prompt: Natural language description of the template to create.

        Yields:
            StreamEvent objects (thinking, content, template, done, error).
        """
        logger.info("BlueprintsService: generate_template_stream called")
        async for event in self._graph.generate_stream(prompt):
            yield event

    async def get_context(self) -> list[dict[str, Any]]:
        """Return conversation context entities from the active graph session.

        Returns:
            List of entity metadata dicts added during this session.
        """
        return self._graph.get_context_entities()

    def clear_context(self) -> None:
        """Clear conversation context."""
        self._graph.clear_context()
