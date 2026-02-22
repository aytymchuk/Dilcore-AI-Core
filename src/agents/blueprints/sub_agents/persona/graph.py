"""Persona LangGraph — resolves user intents to forms/views with data context.

Graph flow:
    retrieve_metadata → retrieve_data → resolve_intent → END
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.documents import Document
from langgraph.graph import END, StateGraph
from typing_extensions import TypedDict

from agents.blueprints.sub_agents.persona.nodes.resolve import ResolveIntentNode
from api.schemas.persona import PersonaRequest, PersonaResponse
from infrastructure.llm import create_embeddings, create_llm
from shared.config import Settings
from store.vector import FaissVectorStore

logger = logging.getLogger(__name__)


class PersonaState(TypedDict):
    """State flowing through the Persona sub-agent graph."""

    user_request: str
    context: dict[str, Any] | None
    relevant_forms: list[dict[str, Any]]
    relevant_views: list[dict[str, Any]]
    relevant_data: list[dict[str, Any]]
    persona_response: PersonaResponse | None
    error: str | None


class RetrieveMetadataNode:
    """Retrieve relevant forms and views from the metadata vector store."""

    def __init__(self, vector_store: FaissVectorStore | None) -> None:
        self._vector_store = vector_store

    async def __call__(self, state: PersonaState) -> dict[str, Any]:
        query = state["user_request"]
        if self._vector_store is None:
            return {"relevant_forms": [], "relevant_views": []}

        forms = self._vector_store.similarity_search(query, top_k=3, filter_dict={"type": "form"})
        views = self._vector_store.similarity_search(query, top_k=3, filter_dict={"type": "view"})
        return {"relevant_forms": forms, "relevant_views": views}


class RetrieveDataNode:
    """Retrieve relevant data records from the data vector store."""

    def __init__(self, vector_store: FaissVectorStore | None) -> None:
        self._vector_store = vector_store

    async def __call__(self, state: PersonaState) -> dict[str, Any]:
        query = state["user_request"]
        if self._vector_store is None:
            return {"relevant_data": []}
        data = self._vector_store.similarity_search(query, top_k=5)
        return {"relevant_data": data}


class PersonaGraph:
    """Encapsulates the compiled Persona LangGraph sub-agent.

    Responsible for:
    - Loading metadata and data FAISS stores.
    - Wiring the retrieve_metadata → retrieve_data → resolve_intent graph.
    - Exposing a simple ``process(request)`` async API.
    - Providing ``index_metadata`` / ``index_data`` helpers for ingestion.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm = create_llm(settings)
        self._embeddings = create_embeddings(settings)

        self._metadata_store = FaissVectorStore(
            embeddings=self._embeddings,
            index_path=settings.vector_store.metadata_index_path,
        )
        self._metadata_store.load()

        self._data_store = FaissVectorStore(
            embeddings=self._embeddings,
            index_path=settings.vector_store.data_index_path,
        )
        self._data_store.load()

        self._graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(PersonaState)
        workflow.add_node("retrieve_metadata", RetrieveMetadataNode(self._metadata_store))
        workflow.add_node("retrieve_data", RetrieveDataNode(self._data_store))
        workflow.add_node("resolve_intent", ResolveIntentNode(self._llm))
        workflow.set_entry_point("retrieve_metadata")
        workflow.add_edge("retrieve_metadata", "retrieve_data")
        workflow.add_edge("retrieve_data", "resolve_intent")
        workflow.add_edge("resolve_intent", END)
        return workflow.compile()

    async def process(self, request: PersonaRequest) -> PersonaResponse:
        """Process a persona request through the graph.

        Args:
            request: PersonaRequest with user's natural language request.

        Returns:
            PersonaResponse with resolved form/view and explanation.
        """
        initial_state: dict[str, Any] = {
            "user_request": request.user_request,
            "context": request.context,
            "relevant_forms": [],
            "relevant_views": [],
            "relevant_data": [],
            "error": None,
        }
        result = await self._graph.ainvoke(initial_state)
        return result["persona_response"]

    async def index_metadata(self, metadata: dict[str, Any], metadata_type: str) -> None:
        """Index a metadata document into the metadata vector store.

        Args:
            metadata: JSON metadata to index.
            metadata_type: Category (form, view, entity, etc.).
        """
        text_parts = [f"Type: {metadata_type}"]
        for key in ("id", "name", "description"):
            if key in metadata:
                text_parts.append(f"{key.title()}: {metadata[key]}")
        doc = Document(
            page_content=" | ".join(text_parts),
            metadata={"type": metadata_type, "id": metadata.get("id", ""), "raw": metadata},
        )
        self._metadata_store.add_document(doc)

    async def index_data(self, data: dict[str, Any], entity_type: str) -> None:
        """Index a data record into the data vector store.

        Args:
            data: Data record to index.
            entity_type: Entity type this record belongs to.
        """
        text_parts = [f"Entity: {entity_type}"]
        for key, val in data.items():
            if isinstance(val, str | int | float | bool):
                text_parts.append(f"{key}: {val}")
        doc = Document(
            page_content=" | ".join(text_parts),
            metadata={"entity_type": entity_type, "id": data.get("id", ""), "raw": data},
        )
        self._data_store.add_document(doc)
