"""Root dependency injection container."""

from dependency_injector import containers, providers

from application.container import ApplicationContainer
from infrastructure.container import InfrastructureContainer
from shared.container import SharedContainer


class Container(containers.DeclarativeContainer):
    """Root container for the application."""

    shared = providers.Container(SharedContainer)

    infrastructure = providers.Container(InfrastructureContainer, shared=shared)

    application = providers.Container(ApplicationContainer, infrastructure=infrastructure)
