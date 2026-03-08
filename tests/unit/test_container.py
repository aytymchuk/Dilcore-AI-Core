"""Unit tests for the dependency injection container."""

from container import Container
from infrastructure.tenant_provider import HeaderTenantProvider
from shared.config import Settings


def test_container_provides_settings():
    """Verify that the container provides settings."""
    container = Container()
    settings = container.shared.settings()
    assert isinstance(settings, Settings)


def test_container_provides_tenant_provider():
    """Verify that the container provides HeaderTenantProvider."""
    container = Container()
    provider = container.infrastructure.tenant_provider()
    assert isinstance(provider, HeaderTenantProvider)


def test_container_singleton_instances():
    """Verify that providers return singleton instances where expected."""
    container = Container()
    p1 = container.infrastructure.tenant_provider()
    p2 = container.infrastructure.tenant_provider()
    assert p1 is p2
