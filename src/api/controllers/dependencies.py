"""FastAPI dependency injection for the new layered architecture."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from application.abstractions.abc_tenant_provider import AbcTenantProvider
from application.services import BlueprintsService
from infrastructure.auth import UserContextDep
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


async def get_tenant_provider() -> AbcTenantProvider:
    from infrastructure.tenant_provider import HeaderTenantProvider

    return HeaderTenantProvider()


TenantContextDep = Annotated[AbcTenantProvider, Depends(get_tenant_provider)]


async def enrich_request_span(
    tenant_provider: TenantContextDep,
    user_provider: UserContextDep,
) -> None:
    """
    FastAPI dependency that enriches the current OpenTelemetry request span
    with context extracted from preceding dependencies (like tenant and auth).

    This allows keeping OpenTelemetry imports out of our domain/infrastructure providers.
    """
    from opentelemetry import trace

    from shared.constants import UNKNOWN_CONTEXT_VALUE

    span = trace.get_current_span()
    if span.is_recording():
        tenant_id = tenant_provider.get_tenant_id()
        user_id = user_provider.get_user_id()

        if tenant_id != UNKNOWN_CONTEXT_VALUE:
            span.set_attribute("tenant.id", tenant_id)

        if user_id != UNKNOWN_CONTEXT_VALUE:
            span.set_attribute("user.id", user_id)
