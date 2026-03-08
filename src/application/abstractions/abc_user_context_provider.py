"""Abstraction for resolving the current user context."""

from abc import ABC, abstractmethod

from application.abstractions.abc_user_id_provider import AbcUserIdProvider
from application.domain.current_user import CurrentUser


class AbcCurrentUserResolver(ABC):
    """Abstract base class for resolving the current user context."""

    @abstractmethod
    def resolve_current_user(self) -> CurrentUser:
        """Resolve and return the current user's claims.

        Returns:
            CurrentUser instance.
        Raises:
            AuthenticationError: On authentication failure.
        """
        pass


class AbcUserContextProvider(AbcUserIdProvider, AbcCurrentUserResolver, ABC):
    """Composite interface for backward compatibility."""

    pass
