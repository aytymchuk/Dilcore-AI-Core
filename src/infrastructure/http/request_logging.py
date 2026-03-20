"""Log outbound httpx calls: HTTP method and full URL (path + query string)."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


def log_httpx_request_sync(request: httpx.Request) -> None:
    """``event_hooks['request']`` hook for :class:`httpx.Client`."""
    logger.info("Outbound HTTP %s %s", request.method, request.url)


async def log_httpx_request_async(request: httpx.Request) -> None:
    """``event_hooks['request']`` hook for :class:`httpx.AsyncClient`."""
    logger.info("Outbound HTTP %s %s", request.method, request.url)
