import logging

from application.abstractions.abc_tenant_provider import AbcTenantProvider
from application.abstractions.abc_user_context_provider import AbcUserContextProvider


class TenantLogFilter(logging.Filter):
    """
    Custom logging.Filter that injects tenant.id attribute
    into every standard python log record.
    """

    def __init__(self, tenant_provider: AbcTenantProvider):
        super().__init__()
        self._tenant_provider = tenant_provider

    def filter(self, record: logging.LogRecord) -> bool:
        """Retrieve tenant ID from context and set as log record attribute."""
        tenant_id = self._tenant_provider.get_tenant_id()
        setattr(record, "tenant.id", tenant_id)
        return True


class UserLogFilter(logging.Filter):
    """
    Custom logging.Filter that injects user.id attribute
    into every standard python log record.
    """

    def __init__(self, user_provider: AbcUserContextProvider):
        super().__init__()
        self._user_provider = user_provider

    def filter(self, record: logging.LogRecord) -> bool:
        """Retrieve user ID from context and set as log record attribute."""
        user_id = self._user_provider.get_user_id()
        setattr(record, "user.id", user_id)
        return True
