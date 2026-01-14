"""Tests for configuration module."""

import os
from unittest.mock import patch

import pytest

from ai_agent.config.settings import Settings, get_settings


class TestSettings:
    """Test cases for Settings class."""

    def test_settings_loads_from_env(self) -> None:
        """Settings should load values from environment variables."""
        env_vars = {
            "OPENROUTER__API_KEY": "test-key-123",
            "OPENROUTER__MODEL": "anthropic/claude-3",
            "APP_NAME": "Custom App Name",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            get_settings.cache_clear()
            settings = Settings()
            
            assert settings.openrouter.api_key.get_secret_value() == "test-key-123"
            assert settings.openrouter.model == "anthropic/claude-3"
            assert settings.app_name == "Custom App Name"

    def test_settings_uses_defaults(self) -> None:
        """Settings should use default values when env vars not set."""
        # Use minimal env vars - only what's required
        # Use clear=True to completely isolate from .env file
        env_vars = {
            "OPENROUTER__API_KEY": "test-key",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            # Disable .env file loading by passing _env_file=None
            settings = Settings(_env_file=None)

            assert settings.openrouter.base_url == "https://openrouter.ai/api/v1"
            assert settings.openrouter.model == "openai/gpt-oss-20b:free"
            assert settings.app_debug is False
            assert settings.log_level == "INFO"

    def test_secret_str_hides_api_key(self) -> None:
        """API key should be hidden when converted to string."""
        env_vars = {
            "OPENROUTER__API_KEY": "super-secret-key",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            get_settings.cache_clear()
            settings = Settings()
            
            # SecretStr should not expose value in string representation
            assert "super-secret-key" not in str(settings.openrouter.api_key)
            assert "super-secret-key" not in repr(settings.openrouter.api_key)

    def test_get_settings_is_cached(self) -> None:
        """get_settings should return cached instance."""
        env_vars = {
            "OPENROUTER__API_KEY": "test-key",
        }
        
        with patch.dict(os.environ, env_vars, clear=False):
            get_settings.cache_clear()
            settings1 = get_settings()
            settings2 = get_settings()
            
            assert settings1 is settings2
