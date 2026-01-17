"""API routes for the template generation service."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status

from ai_agent.schemas import GenerateRequest, TemplateResponse

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
        HTTPException: If template generation fails.
    """
    logger.info("Received template generation request")

    try:
        template = await agent.generate_template(request.prompt)
        return template
    except ValueError as e:
        logger.error("Template generation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        ) from e
