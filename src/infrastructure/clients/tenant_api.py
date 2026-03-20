from __future__ import annotations

import httpx

from application.abstractions.abstract_api_client import ApiClientInterface
from application.abstractions.accesstoken_accessor import AccessTokenAccessor
from application.domain.tenant import TenantInfo
from infrastructure.constants import TENANT_CURRENT_ENDPOINT
from infrastructure.http.http_retry import async_retry_http, sync_retry_http
from infrastructure.http.request_logging import log_httpx_request_async, log_httpx_request_sync


async def fetch_current_tenant_async(
    base_url: str,
    bearer_token: str,
    *,
    timeout_seconds: float = 30.0,
    x_tenant: str | None = None,
    max_retries: int = 3,
    retry_base_delay_seconds: float = 0.25,
    retry_max_delay_seconds: float = 8.0,
) -> TenantInfo:
    """GET ``/tenants/current`` from the platform API (async; for middleware)."""
    base = base_url.rstrip("/")
    timeout = httpx.Timeout(timeout_seconds, connect=min(10.0, timeout_seconds))

    async with httpx.AsyncClient(
        base_url=base,
        timeout=timeout,
        event_hooks={"request": [log_httpx_request_async]},
    ) as client:

        async def _get() -> TenantInfo:
            headers: dict[str, str] = {"Authorization": f"Bearer {bearer_token}"}
            if x_tenant and x_tenant.strip():
                headers["x-tenant"] = x_tenant.strip()
            resp = await client.get(TENANT_CURRENT_ENDPOINT, headers=headers)
            resp.raise_for_status()
            return TenantInfo.model_validate(resp.json())

        return await async_retry_http(
            _get,
            max_retries=max_retries,
            base_delay_seconds=retry_base_delay_seconds,
            max_delay_seconds=retry_max_delay_seconds,
        )


class TenantApiClient(ApiClientInterface):
    """HTTP client to fetch tenant information from the Platform API.

    This client uses a token accessor to obtain the per-request access token
    and forwards it as a Bearer token in the Authorization header.
    """

    def __init__(
        self,
        base_url: str,
        token_accessor: AccessTokenAccessor,
        timeout_seconds: float = 30.0,
        max_retries: int = 3,
        retry_base_delay_seconds: float = 0.25,
        retry_max_delay_seconds: float = 8.0,
    ):
        self.base_url = base_url.rstrip("/")
        timeout = httpx.Timeout(timeout_seconds, connect=min(10.0, timeout_seconds))
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            event_hooks={"request": [log_httpx_request_sync]},
        )
        self._token_accessor = token_accessor
        self._max_retries = max_retries
        self._retry_base_delay_seconds = retry_base_delay_seconds
        self._retry_max_delay_seconds = retry_max_delay_seconds

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def _auth_header(self) -> dict[str, str]:
        token = self._token_accessor.get_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def get_current_tenant(self) -> TenantInfo:
        """Fetch the current tenant information from the API."""
        url = TENANT_CURRENT_ENDPOINT

        def _get() -> TenantInfo:
            headers = self._auth_header()
            resp = self._client.get(url, headers=headers)
            resp.raise_for_status()
            return TenantInfo.model_validate(resp.json())

        return sync_retry_http(
            _get,
            max_retries=self._max_retries,
            base_delay_seconds=self._retry_base_delay_seconds,
            max_delay_seconds=self._retry_max_delay_seconds,
        )
