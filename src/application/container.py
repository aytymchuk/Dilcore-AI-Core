"""Application dependency injection container."""

from dependency_injector import containers, providers


class ApplicationContainer(containers.DeclarativeContainer):
    """Container for application layer dependencies."""

    infrastructure = providers.DependenciesContainer()
