from typing import Protocol


class ITenantProvider(Protocol):
    """Interface for extracting tenant and user information."""

    def get_tenant_id(self) -> str:
        """Get the current tenant ID."""
        ...

    def get_user_id(self) -> str:
        """Get the current user ID."""
        ...
