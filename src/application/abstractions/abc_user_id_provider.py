"""Abstraction for providing the current user ID."""

from abc import ABC, abstractmethod


class AbcUserIdProvider(ABC):
    """Abstract base class for providing the current user ID."""

    @abstractmethod
    def get_user_id(self) -> str:
        """Get the current user id (e.g. from context variables).

        Returns:
            String representing the user ID, or a default string like 'UNKNOWN' if no user is present.
        """
        pass
