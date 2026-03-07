"""Pytest fixtures and configuration."""

from collections.abc import Generator

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


@pytest.fixture
def test_client(mock_env_vars: None) -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    from main import app

    with TestClient(app) as client:
        yield client


@pytest.fixture
def authenticated_client(mock_env_vars: None) -> Generator[TestClient, None, None]:
    """Create an authenticated test client with common dependency overrides."""
    from unittest.mock import MagicMock

    from api.controllers.dependencies import get_blueprints_service
    from application.domain.current_user import CurrentUser
    from infrastructure.auth import get_user_context_provider, verify_token
    from main import app

    # Mock resolver and user
    mock_user = CurrentUser(user_id="test-user", email="test@example.com")
    mock_resolver = MagicMock()
    mock_resolver.resolve_current_user.return_value = mock_user
    # Also mock get_user_id for ambient context if needed
    mock_resolver.get_user_id.return_value = "test-user"

    app.dependency_overrides[get_blueprints_service] = lambda: MagicMock()
    app.dependency_overrides[verify_token] = lambda: "mock_token"
    app.dependency_overrides[get_user_context_provider] = lambda: mock_resolver

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()
