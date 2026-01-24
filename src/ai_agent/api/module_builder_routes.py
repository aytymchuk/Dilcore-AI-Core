"""API routes for Module Builder agent (formerly template generation)."""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sse_starlette.sse import EventSourceResponse

from ai_agent.agent import AgentRegistry, ModuleBuilderAgent, StreamingModuleBuilderAgent
from ai_agent.config import Settings
from ai_agent.schemas import GenerateRequest, TemplateResponse

from .dependencies import get_settings

router = APIRouter(
    prefix="/api/v1/module-builder",
    tags=["Module Builder Agent"],
)


@router.post(
    "/generate",
    response_model=TemplateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate metadata template",
    description="Generate a structured metadata template based on a natural language prompt.",
)
async def generate_template(
    request: GenerateRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> TemplateResponse:
    """Generate a structured template based on the provided prompt.

    The agent uses LLM to generate metadata and can reference existing
    entities from the vector store to suggest relationships.
    """
    agent: ModuleBuilderAgent = AgentRegistry.get_agent("module-builder", settings)
    return await agent.generate_template(request.prompt)


@router.post(
    "/generate-stream",
    status_code=status.HTTP_200_OK,
    summary="Stream metadata generation",
    description="Stream template generation with real-time updates via Server-Sent Events.",
)
async def generate_template_stream(
    request: GenerateRequest,
    settings: Annotated[Settings, Depends(get_settings)],
) -> EventSourceResponse:
    """Stream template generation with SSE.

    Returns a stream of events including thinking (if model supports),
    content chunks, final template, and completion status.
    """
    agent: StreamingModuleBuilderAgent = AgentRegistry.get_agent("module-builder-streaming", settings)

    async def event_generator():
        async for event in agent.generate_template_stream(request.prompt):
            yield {
                "event": event.event_type.value,
                "data": event.data if isinstance(event.data, str) else str(event.data),
            }

    return EventSourceResponse(event_generator())
