"""Streaming API routes for SSE-based template generation."""

from __future__ import annotations

import logging

from fastapi import APIRouter, status
from fastapi.responses import StreamingResponse

from ai_agent.schemas import GenerateRequest
from ai_agent.schemas.errors import ProblemDetails

from .dependencies import StreamingAgentDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])


@router.post(
    "/generate-stream",
    status_code=status.HTTP_200_OK,
    summary="Stream Template Generation",
    description="""
Stream the template generation process using Server-Sent Events (SSE).

**Event Types:**
- `thinking`: Reasoning/thinking content chunks (if model supports thinking mode)
- `content`: Main content generation chunks
- `template`: Final structured template with explanation
- `error`: Error event if generation fails
- `done`: Stream completion marker

**Response Format:** Each event is sent as `data: {json}\\n\\n` in SSE format.
    """,
    responses={
        200: {
            "description": "Successfully streaming template generation",
            "content": {
                "text/event-stream": {
                    "example": "data: {\"event_type\":\"content\",\"data\":\"...\"}\n\n"
                }
            },
        },
        422: {
            "description": "Validation error",
            "model": ProblemDetails,
        },
        500: {
            "description": "Template generation error",
            "model": ProblemDetails,
        },
        502: {
            "description": "LLM provider error",
            "model": ProblemDetails,
        },
    },
)
async def generate_template_stream(
    request: GenerateRequest,
    agent: StreamingAgentDep,
) -> StreamingResponse:
    """Stream template generation with thinking mode support.

    This endpoint streams the AI generation process in real-time using
    Server-Sent Events (SSE). It supports models with or without thinking
    mode, streaming thinking content first (if available), followed by
    the generation content, and finally the complete template with explanation.

    Args:
        request: The generation request containing the user's prompt.
        agent: The streaming AI template agent (injected).

    Returns:
        StreamingResponse with SSE events.
    """
    logger.info("Received streaming template generation request")

    async def event_generator():
        """Generate SSE events from the streaming agent."""
        async for event in agent.generate_template_stream(request.prompt):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        },
    )
