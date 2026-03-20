"""Root dependency injection container."""

from __future__ import annotations

from dependency_injector import containers, providers

from agents.container import AgentsContainer
from application.container import ApplicationContainer
from infrastructure.container import InfrastructureContainer
from shared.container import SharedContainer


class Container(containers.DeclarativeContainer):
    """Root container for the application."""

    shared = providers.Container(SharedContainer)

    infrastructure = providers.Container(InfrastructureContainer, shared=shared)

    agents = providers.Container(AgentsContainer, shared=shared, infrastructure=infrastructure)

    application = providers.Container(
        ApplicationContainer,
        infrastructure=infrastructure,
        agents=agents,
        shared=shared,
    )


_app_container: Container | None = None


def get_app_container() -> Container:
    """Return the process-wide root container (lazy singleton)."""
    global _app_container
    if _app_container is None:
        _app_container = Container()
    return _app_container
