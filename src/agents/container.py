"""Agents-layer dependency injection container."""

from dependency_injector import containers, providers

from agents.blueprints.runtime import build_blueprints_runtime


class AgentsContainer(containers.DeclarativeContainer):
    """Container for agent graphs and related runtimes."""

    shared = providers.DependenciesContainer()
    infrastructure = providers.DependenciesContainer()

    blueprints_runtime = providers.Singleton(
        build_blueprints_runtime,
        settings=shared.settings,
        # Header-based tenant: same x-tenant as routing/auth, no platform HTTP on checkpoint resolve
        tenant_provider=infrastructure.tenant_provider,
    )
