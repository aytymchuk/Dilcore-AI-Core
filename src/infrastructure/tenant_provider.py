import contextvars
from typing import Annotated

from fastapi import Header

from application.abstractions.abc_tenant_provider import AbcTenantProvider
from shared.constants import TENANT_CONTEXT_KEY, UNKNOWN_CONTEXT_VALUE

_tenant_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(TENANT_CONTEXT_KEY, default=UNKNOWN_CONTEXT_VALUE)


class HeaderTenantProvider(AbcTenantProvider):
    """
    Implementation of AbcTenantProvider that retrieves tenant ID
    from async context variables.
    """

    def get_tenant_id(self) -> str:
        """Return tenant ID from context variable."""
        return _tenant_id_var.get()


async def extract_tenant_header(
    x_tenant: Annotated[str, Header(description="Tenant identifier")],
) -> str:
    """
    FastAPI dependency to extract the mandatory x-tenant header and set it in the context.
    """
    _tenant_id_var.set(x_tenant)

    return x_tenant
