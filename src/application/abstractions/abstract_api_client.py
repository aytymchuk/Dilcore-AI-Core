from __future__ import annotations

from abc import ABC, abstractmethod

from application.domain.tenant import TenantInfo


class ApiClientInterface(ABC):
    """Interface for platform/API clients.

    Provides a single, tenant-specific method surface for now.
    """

    @abstractmethod
    def get_current_tenant(self) -> TenantInfo:
        """Return the current tenant information from the Platform API."""
        ...
