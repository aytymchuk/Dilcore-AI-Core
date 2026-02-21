"""Persona controller — intent resolution and vector store indexing."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, status

from api.controllers.dependencies import PersonaGraphDep
from api.schemas import (
    DataIndexRequest,
    DataIndexResponse,
    MetadataIndexRequest,
    MetadataIndexResponse,
    PersonaRequest,
    PersonaResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/persona", tags=["Persona Agent"])


@router.post(
    "/resolve",
    response_model=PersonaResponse,
    status_code=status.HTTP_200_OK,
    summary="Resolve user intent",
    description="Resolve user intent and provide form/view with relevant data.",
)
async def resolve_intent(
    request: PersonaRequest,
    graph: PersonaGraphDep,
) -> PersonaResponse:
    """Resolve intent via the Persona sub-agent graph."""
    return await graph.process(request)


@router.post(
    "/index-metadata",
    response_model=MetadataIndexResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Index metadata",
    description="Index metadata JSON into the vector store for future retrieval.",
)
async def index_metadata(
    request: MetadataIndexRequest,
    graph: PersonaGraphDep,
) -> MetadataIndexResponse:
    """Index metadata into the vector store."""
    try:
        await graph.index_metadata(request.metadata, request.metadata_type)
        return MetadataIndexResponse(
            success=True,
            message=f"Successfully indexed {request.metadata_type} metadata",
            metadata_id=request.metadata.get("id", "unknown"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index metadata: {exc}",
        ) from exc


@router.post(
    "/index-data",
    response_model=DataIndexResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Index data record",
    description="Index a data record into the vector store for semantic search.",
)
async def index_data(
    request: DataIndexRequest,
    graph: PersonaGraphDep,
) -> DataIndexResponse:
    """Index a data record into the vector store."""
    try:
        await graph.index_data(request.data, request.entity_type)
        return DataIndexResponse(
            success=True,
            message=f"Successfully indexed {request.entity_type} data",
            data_id=request.data.get("id", "unknown"),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to index data: {exc}",
        ) from exc


@router.get("/metadata-types", summary="List metadata types")
async def list_metadata_types() -> dict:
    """List supported metadata types for indexing."""
    return {"types": ["form", "view", "entity", "projection", "relationship", "workflow"]}
