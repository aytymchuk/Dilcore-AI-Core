"""FastAPI dependency injection for the new layered architecture."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from application.services import BlueprintsService
from shared.config import Settings, get_settings

# ------------------------------------------------------------------
# Settings
# ------------------------------------------------------------------
SettingsDep = Annotated[Settings, Depends(get_settings)]

# ------------------------------------------------------------------
# Singletons — created once, stored at module level
# ------------------------------------------------------------------
_blueprints_service: BlueprintsService | None = None


def get_blueprints_service(settings: SettingsDep) -> BlueprintsService:
    """Provide the BlueprintsService singleton."""
    global _blueprints_service  # noqa: PLW0603
    if _blueprints_service is None:
        _blueprints_service = BlueprintsService(settings)
    return _blueprints_service


BlueprintsServiceDep = Annotated[BlueprintsService, Depends(get_blueprints_service)]
