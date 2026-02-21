"""Health controller — system status endpoint."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, status

from api.controllers.dependencies import SettingsDep

health_router = APIRouter(prefix="/api/v1", tags=["system"])


@health_router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(settings: SettingsDep) -> dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.app_name,
        "model": settings.openrouter.model,
    }
