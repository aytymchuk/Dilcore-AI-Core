"""Vector search tool — wraps FAISS similarity search as a LangChain tool.

Can be bound to an agent's LLM so the model may call it on demand, or
invoked explicitly in graph nodes.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.tools import tool

logger = logging.getLogger(__name__)

# The store reference is set at graph construction time.
_store: Any = None


def set_store(store: Any) -> None:
    """Register the vector store instance used by this tool.

    Args:
        store: A FaissVectorStore (or compatible) instance.
    """
    global _store  # noqa: PLW0603
    _store = store


@tool
def vector_search_tool(query: str, top_k: int = 5) -> list[dict[str, Any]]:
    """Search the metadata vector store for entities related to *query*.

    Args:
        query: Natural language search query.
        top_k: Maximum number of results to return.

    Returns:
        List of matching entity metadata dicts.
    """
    if _store is None:
        logger.warning("vector_search_tool called but no store is registered")
        return []
    return _store.similarity_search(query=query, top_k=top_k)
