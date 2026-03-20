from __future__ import annotations

from abc import ABC, abstractmethod


class AccessTokenAccessor(ABC):
    """Interface to obtain the per-request access token for outbound calls."""

    @abstractmethod
    def get_token(self) -> str | None:
        raise NotImplementedError
