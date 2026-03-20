from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TenantInfo(BaseModel):
    """Represents a tenant as returned by /tenants/current.

    This model is used by the tenant provider to resolve tenant-scoped
    configuration and storage identifiers.
    """

    id: str
    name: str
    system_name: str = Field(alias="systemName")
    description: str | None = None
    storage_identifier: str = Field(alias="storageIdentifier")
    created_at: datetime = Field(alias="createdAt")

    model_config = ConfigDict(populate_by_name=True)
