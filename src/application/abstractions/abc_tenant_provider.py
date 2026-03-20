from abc import ABC, abstractmethod

from application.domain.tenant import TenantInfo


class AbcTenantProvider(ABC):
    """Interface for extracting tenant information."""

    @abstractmethod
    def get_tenant_id(self) -> str:
        """Get the current tenant ID."""

    @abstractmethod
    def get_tenant_info(self) -> TenantInfo:
        """Return the current tenant (id, storage identifier, etc.)."""
