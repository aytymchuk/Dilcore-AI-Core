"""Pytest fixtures and configuration."""

import os
from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session", autouse=True)
def mock_env_vars() -> Generator[None, None, None]:
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
    }
    
    # Patch Settings to disable .env file loading
    from ai_agent.config.settings import Settings
    original_model_config = Settings.model_config.copy()
    Settings.model_config["env_file"] = None
    
    with patch.dict(os.environ, env_vars, clear=False):
        # Clear cached settings
        from ai_agent.config.settings import get_settings
        get_settings.cache_clear()
        yield
        get_settings.cache_clear()
    
    # Restore original config
    Settings.model_config = original_model_config


@pytest.fixture
def test_client(mock_env_vars: None) -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI application."""
    from ai_agent.main import app
    
    with TestClient(app) as client:
        yield client

