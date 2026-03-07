"""Infrastructure dependency injection container."""

from dependency_injector import containers, providers

from infrastructure.tenant_provider import HeaderTenantProvider
from infrastructure.tracing.telemetry import setup_telemetry
from infrastructure.user_provider import ContextUserProvider


class InfrastructureContainer(containers.DeclarativeContainer):
    """Container for infrastructure layer dependencies."""

    shared = providers.DependenciesContainer()

    tenant_provider = providers.Singleton(HeaderTenantProvider)
    user_provider = providers.Singleton(ContextUserProvider)

    telemetry = providers.Resource(
        setup_telemetry,
        tenant_provider,
        user_provider,
        shared.settings,
    )
