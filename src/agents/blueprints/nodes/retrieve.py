"""Retrieve node — queries the vector store for related entities before generation.

Produces a state update with ``related_entities`` populated so the
``generate`` node can include that context in the prompt.
"""

from __future__ import annotations

import logging
from typing import Any, cast

from agents.blueprints.state import BlueprintsState
from store.vector.faiss_store import FaissVectorStore

logger = logging.getLogger(__name__)


async def retrieve_related_entities_node(state: BlueprintsState) -> dict[str, Any]:
    """Retrieve existing entities related to the current prompt.

    This node uses the vector store tool injected via graph config to find
    entities that may relate to the one being created.

    Args:
        state: Current graph state.

    Returns:
        Partial state update with ``related_entities``.
    """
    vector_store = cast(FaissVectorStore | None, dict(state).get("_vector_store"))
    prompt = state["prompt"]

    if vector_store is None:
        logger.debug("No vector store available — skipping entity retrieval")
        return {"related_entities": []}

    try:
        related = vector_store.similarity_search(
            query=prompt,
            top_k=5,
            filter_dict={"type": "entity"},
        )
        logger.info("Retrieved %d related entities", len(related))
        return {"related_entities": related}
    except Exception as exc:
        logger.warning("Entity retrieval failed: %s", exc)
        return {"related_entities": []}
