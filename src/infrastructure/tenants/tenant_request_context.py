"""Request-scoped tenant resolution: middleware writes, :class:`HeaderTenantProvider` reads."""

from __future__ import annotations

import contextvars

from application.domain.tenant import TenantInfo

RESOLVED_TENANT_INFO_KEY = "resolved_tenant_info"

_resolved_tenant_info: contextvars.ContextVar[TenantInfo | None] = contextvars.ContextVar(
    RESOLVED_TENANT_INFO_KEY, default=None
)


def get_resolved_tenant_info() -> TenantInfo | None:
    """Return platform ``TenantInfo`` for this request, if middleware resolved it."""
    return _resolved_tenant_info.get()


def set_resolved_tenant_info(info: TenantInfo | None) -> None:
    _resolved_tenant_info.set(info)
