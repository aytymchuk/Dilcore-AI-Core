"""Pytest fixtures and configuration."""

from collections.abc import Generator
from datetime import UTC
from typing import Any

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(autouse=True)
def mock_env_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    """Mock environment variables for testing.

    This fixture ensures tests don't depend on the .env file,
    making them reliable in CI/CD environments like GitHub Actions.
    """
    env_vars = {
        "OPENROUTER__API_KEY": "test-api-key-12345",
        "OPENROUTER__BASE_URL": "https://openrouter.ai/api/v1",
        "OPENROUTER__MODEL": "openai/gpt-4o-mini",
        "APP_NAME": "Test AI Agent",
        "APP_DEBUG": "true",
        "LOG_LEVEL": "DEBUG",
        "AUTH0__DOMAIN": "test.auth0.com",
        "AUTH0__CLIENT_ID": "test-client",
        "AUTH0__CLIENT_SECRET": "test-secret",
        "AUTH0__AUDIENCE": "test-audience",
    }

    # Patch Settings to disable .env file loading
    from shared.config.settings import Settings

    monkeypatch.setitem(Settings.model_config, "env_file", None)

    for key, value in env_vars.items():
        monkeypatch.setenv(key, value)

    # Clear cached settings
    from shared.config.settings import get_settings

    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def mock_fetch_current_tenant_async(monkeypatch: pytest.MonkeyPatch) -> None:
    """Avoid real platform HTTP from :class:`TenantResolutionMiddleware` in tests."""

    # Keep _fake aligned with infrastructure.clients.tenant_api.fetch_current_tenant_async:
    # (base_url, bearer_token, **kwargs) -> TenantInfo — update here if that signature changes.
    from datetime import datetime

    from application.domain.tenant import TenantInfo

    async def _fake(base_url: str, bearer_token: str, **kwargs: Any) -> TenantInfo:
        return TenantInfo(
            id="test-tenant",
            name="test-tenant",
            system_name="test-tenant",
            description=None,
            storage_identifier="test-storage",
            created_at=datetime.now(UTC),
        )

    monkeypatch.setattr(
        "infrastructure.clients.tenant_api.fetch_current_tenant_async",
        _fake,
    )


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    from main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def authenticated_client() -> Generator[TestClient, None, None]:
    """Create an authenticated test client with common dependency overrides."""
    from unittest.mock import MagicMock

    from api.controllers.dependencies import get_blueprints_service
    from application.domain.current_user import CurrentUser
    from infrastructure.auth import (
        get_active_user_context_provider,
        get_user_context_provider,
        verify_token,
    )
    from main import app

    # Mock resolver and user
    mock_user = CurrentUser(user_id="test-user", email="test@example.com")
    mock_resolver = MagicMock()
    mock_resolver.resolve_current_user.return_value = mock_user
    # Also mock get_user_id for ambient context if needed
    mock_resolver.get_user_id.return_value = "test-user"

    async def mock_verify_token(*args, **kwargs):
        return None

    app.dependency_overrides[get_blueprints_service] = lambda: MagicMock()
    app.dependency_overrides[verify_token] = mock_verify_token
    app.dependency_overrides[get_active_user_context_provider] = lambda: mock_resolver
    app.dependency_overrides[get_user_context_provider] = lambda: mock_resolver

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
