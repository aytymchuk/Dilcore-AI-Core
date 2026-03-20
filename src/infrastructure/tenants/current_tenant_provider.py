from __future__ import annotations

import logging
import threading
import time

from application.abstractions.abc_tenant_provider import AbcTenantProvider
from application.abstractions.abstract_api_client import ApiClientInterface
from application.domain.tenant import TenantInfo
from infrastructure.http.request_context import get_access_token

logger = logging.getLogger(__name__)


class CurrentTenantProvider(AbcTenantProvider):
    """Tenant provider that fetches current tenant from API with TTL caching."""

    def __init__(
        self,
        api_client: ApiClientInterface,
        *,
        cache_ttl_seconds: float = 3600.0,
    ) -> None:
        self._client = api_client
        self._cache_ttl_seconds = cache_ttl_seconds
        self._cache_lock = threading.Lock()
        self._cached_tenant: TenantInfo | None = None
        self._cache_expiry: float = 0.0
        self._cached_token: str | None = None

    def _current_token(self) -> str | None:
        # Acquire the per-request access token. This token is part of the cache key
        # so that a token change (e.g., new user or refreshed credentials) invalidates
        # the cached TenantInfo appropriately.
        return get_access_token()

    def _load_tenant(self) -> TenantInfo:
        now = time.time()
        token = self._current_token()
        cached = self._cached_tenant
        if cached is not None and now < self._cache_expiry and self._cached_token == token:
            logger.debug(
                "Tenant resolver cache hit id=%s storage_identifier=%s",
                cached.id,
                cached.storage_identifier,
            )
            return cached

        with self._cache_lock:
            now = time.time()
            token = self._current_token()
            if self._cached_tenant is not None and now < self._cache_expiry and self._cached_token == token:
                t = self._cached_tenant
                logger.debug(
                    "Tenant resolver cache hit id=%s storage_identifier=%s",
                    t.id,
                    t.storage_identifier,
                )
                return t

            logger.info("Tenant resolver: fetching current tenant from platform API")
            tenant = self._client.get_current_tenant()
            logger.info(
                "Tenant resolver: resolved id=%s storage_identifier=%s",
                tenant.id,
                tenant.storage_identifier,
            )
            self._cached_tenant = tenant
            self._cached_token = token
            self._cache_expiry = now + self._cache_ttl_seconds
            return tenant

    def get_tenant_id(self) -> str:
        tenant = self._load_tenant()
        return tenant.id

    def get_tenant_info(self) -> TenantInfo:
        """Return the full TenantInfo for the current tenant."""
        return self._load_tenant()
