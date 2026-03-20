from __future__ import annotations

from application.abstractions.accesstoken_accessor import AccessTokenAccessor
from infrastructure.http.request_context import get_access_token


class RequestContextAccessTokenAccessor(AccessTokenAccessor):
    """AccessTokenAccessor implementation backed by per-request context."""

    def get_token(self) -> str | None:
        return get_access_token()
