from contextvars import ContextVar

# Context variables for multitenancy and user tracking
tenant_id_var: ContextVar[str] = ContextVar("tenant_id", default="UNKNOWN")
user_id_var: ContextVar[str] = ContextVar("user_id", default="UNKNOWN")


def get_tenant_id() -> str:
    """Retrieve the current tenant ID from context."""
    return tenant_id_var.get()


def get_user_id() -> str:
    """Retrieve the current user ID from context."""
    return user_id_var.get()
