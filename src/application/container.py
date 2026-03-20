"""Application dependency injection container."""

from dependency_injector import containers, providers

from application.services.blueprints_service import BlueprintsService


class ApplicationContainer(containers.DeclarativeContainer):
    """Container for application layer dependencies."""

    infrastructure = providers.DependenciesContainer()
    agents = providers.DependenciesContainer()
    shared = providers.DependenciesContainer()

    blueprints_service = providers.Singleton(
        BlueprintsService,
        runtime=agents.blueprints_runtime,
    )
