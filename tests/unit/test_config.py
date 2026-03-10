"""Tests for configuration module."""

import json
import os
from unittest.mock import patch

from shared.config.settings import Settings, get_settings


class TestSettings:
    """Test cases for Settings class."""

    AUTH0_TEST_ENV = {
        "AUTHENTICATION__AUTH0__DOMAIN": "test.auth0.com",
        "AUTHENTICATION__AUTH0__CLIENT_ID": "test-id",
        "AUTHENTICATION__AUTH0__CLIENT_SECRET": "test-secret",
        "AUTHENTICATION__AUTH0__AUDIENCE": "test-audience",
    }

    def test_settings_loads_from_env(self) -> None:
        """Settings should load values from environment variables."""
        env_vars = {
            "OPENROUTER__API_KEY": "test-key-123",
            "OPENROUTER__MODEL": "anthropic/claude-3",
            "APPLICATION__NAME": "Custom App Name",
            "AZURE_APPCONFIG_ENDPOINT": "",
            **self.AUTH0_TEST_ENV,
        }

        with patch.dict(os.environ, env_vars, clear=False):
            get_settings.cache_clear()
            settings = Settings()

            assert settings.openrouter.api_key.get_secret_value() == "test-key-123"
            assert settings.openrouter.model == "anthropic/claude-3"
            assert settings.application.name == "Custom App Name"

    def test_settings_uses_defaults(self) -> None:
        """Settings should use default values when env vars not set."""
        env_vars = {
            "OPENROUTER__API_KEY": "test-key",
            **self.AUTH0_TEST_ENV,
        }

        with patch.dict(os.environ, env_vars, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None)

            assert settings.openrouter.base_url == "https://openrouter.ai/api/v1"
            assert settings.openrouter.model == "openai/gpt-oss-20b:free"
            assert settings.application.debug is False
            assert settings.application.log_level == "INFO"
            assert settings.environment == "Development"

    def test_secret_str_hides_api_key(self) -> None:
        """API key should be hidden when converted to string."""
        env_vars = {
            "OPENROUTER__API_KEY": "super-secret-key",
            "AZURE_APPCONFIG_ENDPOINT": "",
            **self.AUTH0_TEST_ENV,
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
            "AZURE_APPCONFIG_ENDPOINT": "",
            **self.AUTH0_TEST_ENV,
        }

        with patch.dict(os.environ, env_vars, clear=False):
            get_settings.cache_clear()
            settings1 = get_settings()
            settings2 = get_settings()

            assert settings1 is settings2

    def test_settings_from_json_dict(self) -> None:
        """Settings should accept PascalCase JSON dict via aliases (simulating App Config)."""
        json_blob = {
            "ApplicationSettings": {
                "Name": "[DEV] Dilcore AI Agent",
                "Version": "0.2.0",
                "Debug": False,
                "LogLevel": "INFO",
                "CorsOrigins": ["*"],
            },
            "OpenRouterSettings": {
                "ApiKey": "json-api-key",
                "BaseUrl": "https://openrouter.ai/api/v1",
                "Model": "google/gemini-2.5-flash-lite",
            },
            "AuthenticationSettings": {
                "Auth0": {
                    "Domain": "json.auth0.com",
                    "ClientId": "json-client-id",
                    "ClientSecret": "json-secret",
                    "Audience": "https://api.json.dilcore.com",
                }
            },
            "MongoDbSettings": {
                "ConnectionString": "mongodb://json-host:27017",
                "DbName": "json_db",
            },
            "VectorStoreSettings": {
                "Provider": "faiss",
                "BasePath": "./json/vector",
                "MetadataIndexName": "json_meta",
                "DataIndexName": "json_data",
                "EmbeddingModel": "openai/text-embedding-3-small",
            },
            "AzureTelemetry": {
                "ApplicationInsightsConnectionString": "InstrumentationKey=json-key",
            },
            "LangSmithSettings": {
                "TracingEnabled": True,
                "Endpoint": "https://eu.api.smith.langchain.com",
                "ApiKey": "json-langsmith-key",
                "Project": "JSON Test Project",
            },
        }

        # Simulate what AzureAppConfigSettingsSource returns
        with patch.dict(os.environ, {}, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None, **json_blob)

        assert settings.application.name == "[DEV] Dilcore AI Agent"
        assert settings.application.version == "0.2.0"
        assert settings.openrouter.api_key.get_secret_value() == "json-api-key"
        assert settings.openrouter.model == "google/gemini-2.5-flash-lite"
        assert settings.authentication.auth0 is not None
        assert settings.authentication.auth0.domain == "json.auth0.com"
        assert settings.mongodb.connection_string == "mongodb://json-host:27017"
        assert settings.mongodb.db_name == "json_db"
        assert settings.vector_store.base_path == "./json/vector"
        assert settings.azure_telemetry.application_insights_connection_string == "InstrumentationKey=json-key"
        assert settings.langsmith.tracing_enabled is True
        assert settings.langsmith.project == "JSON Test Project"

    def test_appsettings_json_roundtrip(self) -> None:
        """The appsettings.json AIAgent section should parse into Settings."""
        import pathlib

        import pytest

        appsettings_path = pathlib.Path(__file__).parents[2] / "appsettings.json"
        if not appsettings_path.exists():
            pytest.skip("appsettings.json fixture missing: expected at repository root")

        raw = json.loads(appsettings_path.read_text())
        ai_agent = raw.get("AIAgent", {})

        # Secrets use $(PLACEHOLDER) in the file — replace with test values
        ai_agent_str = json.dumps(ai_agent)
        ai_agent_str = ai_agent_str.replace("$(AI_AGENT_OPENROUTER_API_KEY)", "test-key")
        ai_agent_str = ai_agent_str.replace("$(AUTH0_DOMAIN)", "test.auth0.com")
        ai_agent_str = ai_agent_str.replace("$(AUTH0_API_DOC_CLIENT_ID)", "test-id")
        ai_agent_str = ai_agent_str.replace("$(AUTH0_API_DOC_CLIENT_SECRET)", "test-secret")
        ai_agent_str = ai_agent_str.replace("$(AUTH0_API_AUDIENCE)", "test-audience")
        ai_agent_str = ai_agent_str.replace("$(AI_AGENT_MONGODB_CONNECTION_STRING)", "mongodb://localhost:27017")
        ai_agent_str = ai_agent_str.replace("$(AI_AGENT_APPLICATION_INSIGHTS_CONNECTION_STRING)", "")
        ai_agent_str = ai_agent_str.replace("$(AI_AGENT_LANGSMITH_API_KEY)", "")
        ai_agent = json.loads(ai_agent_str)

        with patch.dict(os.environ, {}, clear=True):
            get_settings.cache_clear()
            settings = Settings(_env_file=None, **ai_agent)

        assert settings.application.name == "[DEV] Dilcore AI Agent"
        assert settings.openrouter.model == "openai/gpt-oss-20b:free"
        assert settings.authentication.auth0 is not None
        assert settings.authentication.auth0.domain == "test.auth0.com"
