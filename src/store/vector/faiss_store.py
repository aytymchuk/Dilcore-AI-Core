"""FAISS vector store adapter.

Provides a unified interface for loading, querying, and persisting FAISS
indices used by agents (metadata_index and data_index).
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)


class FaissVectorStore:
    """FAISS-backed vector store adapter.

    Wraps langchain_community FAISS with a clean load/save/search API so
    agents and services don't depend on FAISS internals directly.
    """

    def __init__(self, embeddings: OpenAIEmbeddings, index_path: str) -> None:
        """Initialize the store.

        Args:
            embeddings: Embeddings model used for encoding documents.
            index_path: File-system path where the FAISS index is persisted.
        """
        self._embeddings = embeddings
        self._index_path = index_path
        self._store: FAISS | None = None

    def load(self) -> bool:
        """Load the FAISS index from disk.

        Returns:
            True if the index was loaded successfully, False otherwise.
        """
        try:
            self._store = FAISS.load_local(
                self._index_path,
                self._embeddings,
                allow_dangerous_deserialization=True,
            )
            logger.info("Loaded FAISS index from %s", self._index_path)
            return True
        except Exception as exc:
            logger.warning("Could not load FAISS index at %s: %s", self._index_path, exc)
            self._store = None
            return False

    def add_document(self, doc: Document) -> None:
        """Add a single document to the index and persist.

        Args:
            doc: The document to add.
        """
        if self._store is None:
            self._store = FAISS.from_documents([doc], self._embeddings)
        else:
            self._store.add_documents([doc])
        self._store.save_local(self._index_path)
        logger.debug("Indexed document and saved to %s", self._index_path)

    def similarity_search(
        self,
        query: str,
        top_k: int = 5,
        filter_dict: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """Perform similarity search and return raw metadata payloads.

        Args:
            query: Search query text.
            top_k: Number of results to return.
            filter_dict: Optional metadata filter for FAISS.

        Returns:
            List of raw metadata dicts (the ``raw`` field stored per doc).
        """
        if self._store is None:
            return []
        try:
            docs = self._store.similarity_search(query, k=top_k, filter=filter_dict)
            return [doc.metadata.get("raw", {}) for doc in docs]
        except Exception as exc:
            logger.warning("Similarity search failed: %s", exc)
            return []
