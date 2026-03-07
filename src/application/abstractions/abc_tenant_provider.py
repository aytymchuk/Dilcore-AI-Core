from abc import ABC, abstractmethod


class AbcTenantProvider(ABC):
    """Interface for extracting tenant information."""

    @abstractmethod
    def get_tenant_id(self) -> str:
        """Get the current tenant ID."""
        pass
