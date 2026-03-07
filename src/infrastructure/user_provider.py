import contextvars

from application.abstractions.abc_user_context_provider import AbcUserIdProvider
from shared.constants import UNKNOWN_USER_ID, USER_CONTEXT_KEY

_user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(USER_CONTEXT_KEY, default=UNKNOWN_USER_ID)


def set_user_id(user_id: str) -> None:
    """Ensure the user_id is set in the ambient execution context."""
    _user_id_var.set(user_id)


class ContextUserProvider(AbcUserIdProvider):
    """
    Implementation of AbcUserIdProvider that retrieves user context
    from async context variables, primarily for background telemetry where
    active token validation is not available.
    """

    def get_user_id(self) -> str:
        """Retrieve user ID from ambient context. Returns UNKNOWN_USER_ID if not present."""
        return _user_id_var.get()
