"""Abstraction for resolving the current user context."""

from abc import ABC, abstractmethod

from application.domain.current_user import CurrentUser


class IUserContextResolver(ABC):
    """Abstract base class for resolving the current user context."""

    @abstractmethod
    def resolve_current_user(self) -> CurrentUser:
        """Resolve and return the current user's claims.

        Returns:
            CurrentUser instance.
        Raises:
            HTTPException or similar on failure.
        """
        pass
