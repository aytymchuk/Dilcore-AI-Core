"""Shared dependency injection container."""

from dependency_injector import containers, providers

from shared.config import get_settings


class SharedContainer(containers.DeclarativeContainer):
    """Container for shared dependencies like configuration."""

    settings = providers.Singleton(get_settings)
