"""Log outbound httpx calls: method and path (query string omitted to avoid leaking secrets)."""

from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


def _safe_log_target(request: httpx.Request) -> str:
    return request.url.path or "/"


def log_httpx_request_sync(request: httpx.Request) -> None:
    """``event_hooks['request']`` hook for :class:`httpx.Client`."""
    logger.debug("Outbound HTTP %s %s", request.method, _safe_log_target(request))


async def log_httpx_request_async(request: httpx.Request) -> None:
    """``event_hooks['request']`` hook for :class:`httpx.AsyncClient`."""
    logger.debug("Outbound HTTP %s %s", request.method, _safe_log_target(request))
