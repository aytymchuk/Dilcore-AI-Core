"""Persona-based AI agent for user interactions using vector store metadata."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from typing import Any, Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import OpenAIEmbeddings

from ai_agent.config import Settings
from ai_agent.schemas.persona import (
    FormViewResolution,
    PersonaRequest,
    PersonaResponse,
)

from .base import StreamingAgent
from .persona_prompts import FORM_VIEW_RESOLUTION_PROMPT, PERSONA_SYSTEM_PROMPT
from .registry import AgentRegistry

logger = logging.getLogger(__name__)


@AgentRegistry.register("persona")
class PersonaAgent(StreamingAgent):
    """Agent for persona-based interactions using FAISS vector store.

    Has READ access to:
    - metadata_index: Forms, views, entities, projections, relationships, workflows
    - data_index: Actual data records for semantic search

    This agent resolves user requests to appropriate forms/views and
    provides relevant data context for user interactions.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the persona agent.

        Args:
            settings: Application settings containing OpenRouter and vector store config.
        """
        super().__init__(settings)
        self._embeddings = self._create_embeddings()
        self._metadata_store: Optional[FAISS] = None
        self._data_store: Optional[FAISS] = None

        # Load vector stores
        self._load_stores()

    def _create_embeddings(self) -> OpenAIEmbeddings:
        """Create embeddings model for vector store."""
        return OpenAIEmbeddings(
            api_key=self._settings.openrouter.api_key.get_secret_value(),
            base_url=self._settings.openrouter.base_url,
            model=self._settings.vector_store.embedding_model,
        )

    def _load_stores(self) -> None:
        """Load FAISS vector stores for metadata and data."""
        # Load metadata store
        try:
            self._metadata_store = FAISS.load_local(
                self._settings.vector_store.metadata_index_path,
                self._embeddings,
                allow_dangerous_deserialization=True,
            )
            logger.info("Loaded metadata store from %s", self._settings.vector_store.metadata_index_path)
        except Exception as e:
            logger.warning("Could not load metadata store: %s", e)
            self._metadata_store = None

        # Load data store
        try:
            self._data_store = FAISS.load_local(
                self._settings.vector_store.data_index_path,
                self._embeddings,
                allow_dangerous_deserialization=True,
            )
            logger.info("Loaded data store from %s", self._settings.vector_store.data_index_path)
        except Exception as e:
            logger.warning("Could not load data store: %s", e)
            self._data_store = None

    @property
    def agent_type(self) -> str:
        """Return the agent type identifier."""
        return "persona"

    async def index_metadata(self, metadata: dict[str, Any], metadata_type: str) -> None:
        """Index metadata JSON into the metadata vector store.

        Args:
            metadata: JSON metadata to index.
            metadata_type: Type of metadata (form, view, entity, etc.).
        """
        # Create searchable text representation
        doc_text = self._create_searchable_text(metadata, metadata_type)

        # Create document with metadata
        doc = Document(
            page_content=doc_text,
            metadata={
                "type": metadata_type,
                "id": metadata.get("id", ""),
                "name": metadata.get("name", ""),
                "raw": metadata,  # Store full JSON for retrieval
            },
        )

        # Initialize store if not exists
        if self._metadata_store is None:
            self._metadata_store = FAISS.from_documents([doc], self._embeddings)
        else:
            self._metadata_store.add_documents([doc])

        # Persist to disk
        self._metadata_store.save_local(self._settings.vector_store.metadata_index_path)
        logger.info("Indexed %s metadata: %s", metadata_type, metadata.get("id", "unknown"))

    async def index_data(self, data: dict[str, Any], entity_type: str) -> None:
        """Index a data record into the data vector store.

        Args:
            data: The data record to index.
            entity_type: The type of entity this data belongs to.
        """
        # Create searchable text from data fields
        text_parts = [f"Entity: {entity_type}"]
        for key, value in data.items():
            if isinstance(value, (str, int, float, bool)):
                text_parts.append(f"{key}: {value}")
        doc_text = " | ".join(text_parts)

        doc = Document(
            page_content=doc_text,
            metadata={
                "entity_type": entity_type,
                "id": data.get("id", ""),
                "raw": data,
            },
        )

        if self._data_store is None:
            self._data_store = FAISS.from_documents([doc], self._embeddings)
        else:
            self._data_store.add_documents([doc])

        self._data_store.save_local(self._settings.vector_store.data_index_path)
        logger.info("Indexed %s data record: %s", entity_type, data.get("id", "unknown"))

    def _create_searchable_text(self, metadata: dict[str, Any], metadata_type: str) -> str:
        """Convert JSON metadata to searchable text for embedding.

        Args:
            metadata: JSON metadata.
            metadata_type: Type of metadata.

        Returns:
            Searchable text representation.
        """
        parts = [f"Type: {metadata_type}"]

        if "id" in metadata:
            parts.append(f"ID: {metadata['id']}")
        if "name" in metadata:
            parts.append(f"Name: {metadata['name']}")
        if "description" in metadata:
            parts.append(f"Description: {metadata['description']}")

        # Add type-specific fields
        if metadata_type == "form" and "fields" in metadata:
            field_names = [f.get("name", "") for f in metadata.get("fields", [])]
            parts.append(f"Fields: {', '.join(field_names)}")
        elif metadata_type == "view" and "columns" in metadata:
            col_names = [c.get("name", "") for c in metadata.get("columns", [])]
            parts.append(f"Columns: {', '.join(col_names)}")
        elif metadata_type == "entity" and "properties" in metadata:
            prop_names = list(metadata.get("properties", {}).keys())
            parts.append(f"Properties: {', '.join(prop_names)}")

        return " | ".join(parts)

    async def _retrieve_relevant_metadata(
        self,
        query: str,
        metadata_type: Optional[str] = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant metadata from metadata index.

        Args:
            query: Search query.
            metadata_type: Optional filter by metadata type.
            top_k: Number of results to return.

        Returns:
            List of relevant metadata documents.
        """
        if self._metadata_store is None:
            return []

        try:
            filter_dict = {"type": metadata_type} if metadata_type else None
            docs = self._metadata_store.similarity_search(
                query,
                k=top_k,
                filter=filter_dict,
            )
            return [doc.metadata.get("raw", {}) for doc in docs]
        except Exception as e:
            logger.warning("Failed to search metadata store: %s", e)
            return []

    async def _retrieve_relevant_data(
        self,
        query: str,
        entity_type: Optional[str] = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Retrieve relevant data records from data index.

        Args:
            query: Search query.
            entity_type: Optional filter by entity type.
            top_k: Number of results to return.

        Returns:
            List of relevant data records.
        """
        if self._data_store is None:
            return []

        try:
            filter_dict = {"entity_type": entity_type} if entity_type else None
            docs = self._data_store.similarity_search(
                query,
                k=top_k,
                filter=filter_dict,
            )
            return [doc.metadata.get("raw", {}) for doc in docs]
        except Exception as e:
            logger.warning("Failed to search data store: %s", e)
            return []

    async def process(self, request: PersonaRequest) -> PersonaResponse:
        """Process user request to resolve form/view and data.

        Args:
            request: PersonaRequest with user's natural language request.

        Returns:
            PersonaResponse with resolved form/view and suggested changes.
        """
        logger.info("Processing persona request: %s", request.user_request[:100])

        # 1. Query metadata store for relevant forms/views
        relevant_forms = await self._retrieve_relevant_metadata(
            request.user_request,
            metadata_type="form",
            top_k=3,
        )

        relevant_views = await self._retrieve_relevant_metadata(
            request.user_request,
            metadata_type="view",
            top_k=3,
        )

        # 2. Query data store for relevant existing data
        relevant_data = await self._retrieve_relevant_data(
            request.user_request,
            top_k=5,
        )

        # 3. Use LLM to determine the best form/view and suggest actions
        resolution = await self._resolve_with_llm(
            request.user_request,
            relevant_forms,
            relevant_views,
            relevant_data,
            request.context,
        )

        return resolution

    async def _resolve_with_llm(
        self,
        user_request: str,
        forms: list[dict[str, Any]],
        views: list[dict[str, Any]],
        data: list[dict[str, Any]],
        context: Optional[dict[str, Any]],
    ) -> PersonaResponse:
        """Use LLM to resolve the user request to a form/view and actions.

        Args:
            user_request: The user's natural language request.
            forms: Available forms from metadata.
            views: Available views from metadata.
            data: Relevant existing data.
            context: Additional context from the request.

        Returns:
            PersonaResponse with resolution details.
        """
        # Build metadata context
        metadata_items = []
        for form in forms:
            metadata_items.append(f"Form: {form.get('name', form.get('id', 'unknown'))}")
        for view in views:
            metadata_items.append(f"View: {view.get('name', view.get('id', 'unknown'))}")

        metadata_context = "\n".join(metadata_items) if metadata_items else "No metadata available"

        # Build prompt
        messages = [
            SystemMessage(content=PERSONA_SYSTEM_PROMPT),
            HumanMessage(
                content=FORM_VIEW_RESOLUTION_PROMPT.format(
                    user_request=user_request,
                    metadata_context=metadata_context,
                )
            ),
        ]

        try:
            response = await self._llm.ainvoke(messages)

            # Parse LLM response to extract resolution
            # For now, return a default response - full parsing will be implemented
            best_match = forms[0] if forms else (views[0] if views else None)

            if best_match:
                resolution = FormViewResolution(
                    type="form" if forms else "view",
                    id=best_match.get("id", "unknown"),
                    name=best_match.get("name", "Unknown"),
                    operation="read",  # Default operation
                )
            else:
                resolution = FormViewResolution(
                    type="view",
                    id="default",
                    name="Default View",
                    operation="read",
                )

            return PersonaResponse(
                resolution=resolution,
                existing_data=data[0] if data else None,
                suggested_changes=[],
                explanation=response.content if hasattr(response, "content") else str(response),
            )

        except Exception as e:
            logger.exception("Failed to resolve with LLM")
            # Return a fallback response
            return PersonaResponse(
                resolution=FormViewResolution(
                    type="view",
                    id="error",
                    name="Error",
                    operation="read",
                ),
                existing_data=None,
                suggested_changes=[],
                explanation=f"Could not process request: {str(e)}",
            )

    async def process_stream(self, request: Any) -> AsyncGenerator[Any, None]:
        """Stream persona-based interactions.

        Args:
            request: The PersonaRequest to process.

        Yields:
            Response chunks as they become available.
        """
        # For now, yield the complete response
        # Full streaming implementation can be added later
        result = await self.process(request)
        yield result
