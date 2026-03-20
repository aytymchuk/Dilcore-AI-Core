from __future__ import annotations

from contextvars import ContextVar

# Context variable to store per-request access token (Bearer token)
_ACCESS_TOKEN: ContextVar[str | None] = ContextVar("access_token", default=None)


def set_access_token(token: str | None) -> None:
    """Store the per-request access token in context.

    This allows downstream code to fetch the token without threading it
    through every call.
    """
    _ACCESS_TOKEN.set(token)


def get_access_token() -> str | None:
    """Retrieve the per-request access token from context, if set."""
    return _ACCESS_TOKEN.get()
