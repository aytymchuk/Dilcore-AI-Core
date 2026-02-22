"""Streaming controller — legacy /api/v1/metadata/generate-stream endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from api.controllers.dependencies import BlueprintsServiceDep
from api.schemas import GenerateRequest
from api.schemas.errors import ProblemDetails
from shared.streaming import format_sse_event

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])


@router.post(
    "/generate-stream",
    status_code=status.HTTP_200_OK,
    summary="Stream Template Generation (legacy)",
    description="Stream template generation via SSE. Prefer /api/v1/blueprints/generate-stream.",
    responses={
        422: {"description": "Validation error", "model": ProblemDetails},
        500: {"description": "Generation error", "model": ProblemDetails},
        502: {"description": "LLM provider error", "model": ProblemDetails},
    },
)
async def generate_template_stream(
    request: GenerateRequest,
    service: BlueprintsServiceDep,
) -> StreamingResponse:
    """Stream template generation (legacy SSE endpoint)."""
    logger.info("Received legacy streaming generation request")

    async def event_generator():
        async for event in service.generate_template_stream(request.prompt):
            yield format_sse_event(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
