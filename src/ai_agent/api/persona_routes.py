"""API routes for Persona agent."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from ai_agent.agent import AgentRegistry, PersonaAgent
from ai_agent.config import Settings
from ai_agent.schemas import (
    DataIndexRequest,
    DataIndexResponse,
    MetadataIndexRequest,
    MetadataIndexResponse,
    PersonaRequest,
    PersonaResponse,
)

from .dependencies import get_settings

router = APIRouter(
    prefix="/api/v1/persona",
    tags=["Persona Agent"],
)


@router.post(
    "/resolve",
    response_model=PersonaResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve user intent",
    description="Resolve user intent and provide form/view with relevant data.",
)
async def resolve_intent(
    request: PersonaRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PersonaResponse:
    """Resolve user intent and provide form/view with data.

    The agent queries both metadata and data vector stores to find
    the most appropriate form/view and relevant existing data.
    """
    agent: PersonaAgent = AgentRegistry.get_agent("persona", settings)
    return await agent.process(request)


@router.post(
    "/index-metadata",
    response_model=MetadataIndexResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Index metadata",
    description="Index metadata JSON into the vector store for future retrieval.",
)
async def index_metadata(
    request: MetadataIndexRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> MetadataIndexResponse:
    """Index metadata JSON into the vector store.

    This endpoint allows you to store forms, views, entities, and other metadata
    that the persona agent can later retrieve to resolve user requests.
    """
    agent: PersonaAgent = AgentRegistry.get_agent("persona", settings)

    try:
        await agent.index_metadata(request.metadata, request.metadata_type)
        return MetadataIndexResponse(
            success=True,
            message=f"Successfully indexed {request.metadata_type} metadata",
            metadata_id=request.metadata.get("id", "unknown"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index metadata: {str(e)}",
        ) from e


@router.post(
    "/index-data",
    response_model=DataIndexResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Index data record",
    description="Index a data record into the vector store for semantic search.",
)
async def index_data(
    request: DataIndexRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> DataIndexResponse:
    """Index a data record into the vector store.

    This endpoint allows you to store data records that the persona agent
    can retrieve when resolving user requests for existing data.
    """
    agent: PersonaAgent = AgentRegistry.get_agent("persona", settings)

    try:
        await agent.index_data(request.data, request.entity_type)
        return DataIndexResponse(
            success=True,
            message=f"Successfully indexed {request.entity_type} data",
            data_id=request.data.get("id", "unknown"),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index data: {str(e)}",
        ) from e


@router.get(
    "/metadata-types",
    summary="List metadata types",
    description="List supported metadata types for indexing.",
)
async def list_metadata_types() -> dict:
    """List supported metadata types for indexing."""
    return {"types": ["form", "view", "entity", "projection", "relationship", "workflow"]}
