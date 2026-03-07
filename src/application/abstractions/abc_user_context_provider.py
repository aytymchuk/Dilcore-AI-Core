"""Abstraction for resolving the current user context."""

from abc import ABC, abstractmethod

from application.domain.current_user import CurrentUser


class AbcUserContextProvider(ABC):
    """Abstract base class for providing the current user context."""

    @abstractmethod
    def resolve_current_user(self) -> CurrentUser:
        """Resolve and return the current user's claims.

        Returns:
            CurrentUser instance.
        Raises:
            HTTPException or similar on failure.
        """
        pass

    @abstractmethod
    def get_user_id(self) -> str:
        """Get the current user id (e.g. from context variables).

        Returns:
            String representing the user ID, or a default string like 'UNKNOWN' if no user is present.
        """
        pass
