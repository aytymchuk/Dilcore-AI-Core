"""Retrieve node — queries the vector store for related entities before generation.

Produces a state update with ``related_entities`` populated so the
``generate`` node can include that context in the prompt.
"""

from __future__ import annotations

import logging
from typing import Any

from agents.blueprints.state import BlueprintsState
from store.vector.faiss_store import FaissVectorStore

logger = logging.getLogger(__name__)


class RetrieveRelatedEntitiesNode:
    """Retrieve existing entities related to the current prompt."""

    def __init__(self, vector_store: FaissVectorStore | None) -> None:
        """Initialise the node with the vector store dependency.

        Args:
            vector_store: Extracted FAISS index for entities.
        """
        self._vector_store = vector_store

    async def __call__(self, state: BlueprintsState) -> dict[str, Any]:
        """Execute the entity retrieval node logic.

        Args:
            state: Current graph state.

        Returns:
            Partial state update with ``related_entities``.
        """
        prompt = state["prompt"]

        if self._vector_store is None:
            logger.debug("No vector store available — skipping entity retrieval")
            return {"related_entities": []}

        try:
            related = self._vector_store.similarity_search(
                query=prompt,
                top_k=5,
                filter_dict={"type": "entity"},
            )
            logger.info("Retrieved %d related entities", len(related))
            return {"related_entities": related}
        except Exception as exc:
            logger.warning("Entity retrieval failed: %s", exc)
            return {"related_entities": []}
