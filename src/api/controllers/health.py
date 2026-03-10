"""Health controller — system status endpoint."""

from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, status

from api.controllers.dependencies import SettingsDep

health_router = APIRouter(prefix="/api/v1", tags=["system"])


@health_router.get("/health", status_code=status.HTTP_200_OK)
async def health_check(settings: SettingsDep) -> dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "app_name": settings.application.name,
        "model": settings.openrouter.model,
        "version": os.getenv("APP_VERSION", "0.0.0"),
    }
