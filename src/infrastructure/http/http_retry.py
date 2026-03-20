"""Retry transient HTTP failures using tenacity (timeouts, transport errors, 5xx / 429)."""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

import httpx
from tenacity import (
    AsyncRetrying,
    Retrying,
    before_sleep_log,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential_jitter,
)

logger = logging.getLogger(__name__)


def _is_transient_exception(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TimeoutException):
        return True
    if isinstance(exc, (httpx.ConnectError, httpx.ReadError, httpx.WriteError, httpx.RemoteProtocolError)):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        code = exc.response.status_code
        return code in (408, 429) or code >= 500
    return False


def _wait(
    base_delay_seconds: float,
    max_delay_seconds: float,
) -> wait_exponential_jitter:
    jitter = min(max(base_delay_seconds * 0.25, 0.05), 2.0)
    return wait_exponential_jitter(
        initial=base_delay_seconds,
        max=max_delay_seconds,
        exp_base=2,
        jitter=jitter,
    )


async def async_retry_http[T](
    operation: Callable[[], Awaitable[T]],
    *,
    max_retries: int,
    base_delay_seconds: float = 0.25,
    max_delay_seconds: float = 8.0,
) -> T:
    """Run ``operation``; on transient errors retry up to ``max_retries`` times after the first attempt."""
    total_attempts = max(1, 1 + max(0, max_retries))
    async for attempt in AsyncRetrying(
        stop=stop_after_attempt(total_attempts),
        wait=_wait(base_delay_seconds, max_delay_seconds),
        retry=retry_if_exception(_is_transient_exception),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    ):
        with attempt:
            return await operation()
    raise RuntimeError("async_retry_http: no attempt completed")  # pragma: no cover


def sync_retry_http[T](
    operation: Callable[[], T],
    *,
    max_retries: int,
    base_delay_seconds: float = 0.25,
    max_delay_seconds: float = 8.0,
) -> T:
    """Sync variant of :func:`async_retry_http`."""
    total_attempts = max(1, 1 + max(0, max_retries))
    for attempt in Retrying(
        stop=stop_after_attempt(total_attempts),
        wait=_wait(base_delay_seconds, max_delay_seconds),
        retry=retry_if_exception(_is_transient_exception),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.WARNING),
    ):
        with attempt:
            return operation()
    raise RuntimeError("sync_retry_http: no attempt completed")  # pragma: no cover
