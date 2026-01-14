"""Application settings using Pydantic BaseSettings."""

from functools import lru_cache

from pydantic import BaseModel, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenRouterSettings(BaseModel):
    """OpenRouter API configuration."""

    api_key: SecretStr
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "openai/gpt-oss-20b:free"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Application
    app_name: str = "AI Template Agent"
    app_debug: bool = False
    log_level: str = "INFO"

    # OpenRouter - uses OPENROUTER__API_KEY, OPENROUTER__BASE_URL, etc.
    openrouter: OpenRouterSettings


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Using lru_cache ensures settings are only loaded once.
    """
    return Settings()
