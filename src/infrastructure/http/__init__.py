"""HTTP infrastructure — async HTTP client setup.

Intended for outbound HTTP calls to external services.
Uses httpx for async support.
"""

from __future__ import annotations

import httpx


def create_http_client(base_url: str = "", timeout: float = 30.0) -> httpx.AsyncClient:
    """Create a configured async HTTP client.

    Args:
        base_url: Optional base URL for all requests.
        timeout: Request timeout in seconds.

    Returns:
        Configured AsyncClient instance.
    """
    return httpx.AsyncClient(
        base_url=base_url,
        timeout=httpx.Timeout(timeout),
        headers={"User-Agent": "DilcoreAI/1.0"},
    )
