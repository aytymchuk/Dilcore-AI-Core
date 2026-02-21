"""Blueprints (module builder) controller."""

from __future__ import annotations

import logging

from fastapi import APIRouter, status
from sse_starlette.sse import EventSourceResponse

from api.controllers.dependencies import BlueprintsServiceDep
from api.schemas import GenerateRequest, TemplateResponse
from api.schemas.errors import ProblemDetails

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/blueprints", tags=["Blueprints Agent"])


@router.post(
    "/generate",
    response_model=TemplateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate metadata template",
    description="Generate a structured metadata template based on a natural language prompt.",
    responses={
        422: {"description": "Validation error", "model": ProblemDetails},
        500: {"description": "Generation error", "model": ProblemDetails},
        502: {"description": "LLM provider error", "model": ProblemDetails},
    },
)
async def generate_template(
    request: GenerateRequest,
    service: BlueprintsServiceDep,
) -> TemplateResponse:
    """Generate a structured template from the prompt using the Blueprints LangGraph."""
    logger.info("Received generate request")
    return await service.generate_template(request.prompt)


@router.post(
    "/generate-stream",
    status_code=status.HTTP_200_OK,
    summary="Stream metadata generation",
    description="Stream template generation with real-time updates via Server-Sent Events.",
)
async def generate_template_stream(
    request: GenerateRequest,
    service: BlueprintsServiceDep,
) -> EventSourceResponse:
    """Stream template generation with SSE events."""

    async def event_generator():
        async for event in service.generate_template_stream(request.prompt):
            yield {
                "event": event.event_type.value,
                "data": event.data if isinstance(event.data, str) else str(event.data),
            }

    return EventSourceResponse(event_generator())
