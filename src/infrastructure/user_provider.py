import contextvars

from application.abstractions.abc_user_context_provider import AbcUserContextProvider
from application.domain.current_user import CurrentUser
from shared.constants import UNKNOWN_CONTEXT_VALUE, USER_CONTEXT_KEY

_user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(USER_CONTEXT_KEY, default=UNKNOWN_CONTEXT_VALUE)


def set_user_id(user_id: str) -> None:
    """Ensure the user_id is set in the ambient execution context."""
    _user_id_var.set(user_id)


class ContextUserProvider(AbcUserContextProvider):
    """
    Implementation of AbcUserContextProvider that retrieves user context
    from async context variables, primarily for background telemetry where
    active token validation is not available.
    """

    def resolve_current_user(self) -> CurrentUser:
        """Not supported for pure context providers."""
        raise NotImplementedError("Context provider cannot resolve full user details.")

    def get_user_id(self) -> str:
        """Return user ID from context variable."""
        return _user_id_var.get()
