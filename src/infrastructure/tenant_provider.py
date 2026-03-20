import contextvars
import logging
from datetime import UTC, datetime
from typing import Annotated

import httpx
from fastapi import Header
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

from application.abstractions.abc_tenant_provider import AbcTenantProvider
from application.domain.tenant import TenantInfo
from infrastructure.clients.tenant_api import fetch_current_tenant_async
from infrastructure.tenants.tenant_request_context import get_resolved_tenant_info, set_resolved_tenant_info
from shared.config import get_settings
from shared.constants import TENANT_CONTEXT_KEY, UNKNOWN_TENANT_ID

logger = logging.getLogger(__name__)

_tenant_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(TENANT_CONTEXT_KEY, default=UNKNOWN_TENANT_ID)


def _problem_json(
    request: Request,
    *,
    status_code: int,
    title: str,
    detail: str,
    problem_type: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "type": f"https://api.dilcore.ai/problems/{problem_type}",
            "title": title,
            "status": status_code,
            "detail": detail,
            "instance": request.url.path,
        },
    )


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    """Resolve tenant early: ``x-tenant`` for context ordering; platform API when Bearer token is present.

    Stores :class:`~application.domain.tenant.TenantInfo` in request context for
    :class:`HeaderTenantProvider` (checkpointer, OpenTelemetry, etc.).
    """

    async def dispatch(self, request: Request, call_next):
        set_resolved_tenant_info(None)
        _tenant_id_var.set(UNKNOWN_TENANT_ID)

        raw = request.headers.get("x-tenant")
        x_tenant_header = str(raw).strip() if raw and str(raw).strip() else None
        if x_tenant_header:
            _tenant_id_var.set(x_tenant_header)

        auth = request.headers.get("authorization")
        if auth and auth.lower().startswith("bearer "):
            token = auth[7:].strip()
            if token:
                settings = get_settings()
                try:
                    info = await fetch_current_tenant_async(
                        str(settings.api_settings.base_url),
                        token,
                        timeout_seconds=settings.api_settings.tenant_http_timeout_seconds,
                        x_tenant=x_tenant_header,
                        max_retries=settings.api_settings.tenant_http_max_retries,
                        retry_base_delay_seconds=settings.api_settings.tenant_http_retry_base_seconds,
                        retry_max_delay_seconds=settings.api_settings.tenant_http_retry_max_delay_seconds,
                    )
                    set_resolved_tenant_info(info)
                    _tenant_id_var.set(info.name)
                    logger.debug(
                        "Middleware resolved tenant id=%s storageIdentifier=%s",
                        info.id,
                        info.storageIdentifier,
                    )
                except httpx.TimeoutException as exc:
                    logger.error("Platform tenant API timeout: %s", exc)
                    return _problem_json(
                        request,
                        status_code=504,
                        title="Gateway Timeout",
                        detail="The platform API did not respond in time while resolving the tenant.",
                        problem_type="tenant-resolution-timeout",
                    )
                except httpx.HTTPStatusError as exc:
                    logger.warning(
                        "Platform tenant API HTTP %s",
                        exc.response.status_code,
                    )
                    return _problem_json(
                        request,
                        status_code=exc.response.status_code,
                        title="Tenant Resolution Failed",
                        detail=f"Platform tenant API returned HTTP {exc.response.status_code}.",
                        problem_type="tenant-resolution-http-error",
                    )
                except httpx.RequestError as exc:
                    logger.warning("Platform tenant API request error: %s", exc)
                    return _problem_json(
                        request,
                        status_code=503,
                        title="Service Unavailable",
                        detail="Could not reach the platform API to resolve the tenant.",
                        problem_type="tenant-resolution-unavailable",
                    )
                except Exception:
                    logger.exception("Unexpected error resolving tenant from platform API")
                    return _problem_json(
                        request,
                        status_code=503,
                        title="Service Unavailable",
                        detail="Unexpected error while resolving tenant from the platform API.",
                        problem_type="tenant-resolution-failed",
                    )

        return await call_next(request)


class HeaderTenantProvider(AbcTenantProvider):
    """Tenant id and :class:`TenantInfo` from request context (middleware + optional header fallback)."""

    def get_tenant_id(self) -> str:
        return _tenant_id_var.get()

    def get_tenant_info(self) -> TenantInfo:
        resolved = get_resolved_tenant_info()
        if resolved is not None:
            return resolved

        tenant_id = self.get_tenant_id()
        storage_identifier = tenant_id.strip() if tenant_id != UNKNOWN_TENANT_ID and tenant_id.strip() else "default"
        return TenantInfo(
            id=tenant_id,
            name=tenant_id,
            systemName=tenant_id,
            description=None,
            storageIdentifier=storage_identifier,
            createdAt=datetime.now(UTC),
        )


def extract_tenant_header(
    x_tenant: Annotated[str, Header(description="Tenant identifier", alias="x-tenant")],
    authorization: Annotated[str | None, Header(description="Authorization header")] = None,
) -> str:
    """Require ``x-tenant`` and sync token into request context; do not overwrite API-resolved tenant id."""
    if get_resolved_tenant_info() is None:
        _tenant_id_var.set(x_tenant)
    if authorization:
        from infrastructure.http.request_context import set_access_token

        token = authorization.removeprefix("Bearer ").removeprefix("bearer ").strip()
        set_access_token(token)

    return x_tenant
