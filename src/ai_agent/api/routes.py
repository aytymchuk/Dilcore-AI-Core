"""API routes for the template generation service."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, status

from ai_agent.schemas import GenerateRequest, TemplateResponse
from ai_agent.schemas.errors import ProblemDetails

from .dependencies import AgentDep, SettingsDep

logger = logging.getLogger(__name__)

# Health router at /api/v1
health_router = APIRouter(prefix="/api/v1", tags=["system"])

# Metadata router at /api/v1/metadata
router = APIRouter(prefix="/api/v1/metadata", tags=["metadata"])


@health_router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(settings: SettingsDep) -> dict[str, Any]:
    """Health check endpoint.

    Returns basic application status and configuration info.
    """
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "model": settings.openrouter.model,
    }


@router.post(
    "/generate",
    response_model=TemplateResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate Template",
    description="Generate a structured JSON template based on the user's prompt.",
    responses={
        200: {
            "description": "Successfully generated template",
            "model": TemplateResponse,
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
async def generate_template(
    request: GenerateRequest,
    agent: AgentDep,
) -> TemplateResponse:
    """Generate a structured template from the user's prompt.

    Args:
        request: The generation request containing the user's prompt.
        agent: The AI template agent (injected).

    Returns:
        A structured TemplateResponse with sections and fields.

    Raises:
        TemplateGenerationError: If template generation fails.
        LLMProviderError: If LLM provider communication fails.
        TemplateParsingError: If template parsing fails.
    """
    logger.info("Received template generation request")
    template = await agent.generate_template(request.prompt)
    return template
