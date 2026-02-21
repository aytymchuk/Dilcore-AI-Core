"""Application settings using Pydantic BaseSettings."""

from functools import lru_cache

from pydantic import BaseModel, Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenRouterSettings(BaseModel):
    """OpenRouter API configuration."""

    api_key: SecretStr
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "openai/gpt-oss-20b:free"


class VectorStoreSettings(BaseModel):
    """FAISS vector store configuration with separate indices for metadata and data."""

    provider: str = Field(default="faiss", description="Vector store provider (faiss)")
    base_path: str = Field(
        default="./data/vector_store",
        description="Base path for FAISS indices",
    )
    metadata_index_name: str = Field(
        default="metadata_index",
        description="Name of the metadata index (forms, views, entities, etc.)",
    )
    data_index_name: str = Field(
        default="data_index",
        description="Name of the data index (actual records)",
    )
    embedding_model: str = Field(
        default="openai/text-embedding-3-small",
        description="Embedding model to use via OpenRouter",
    )

    @computed_field
    @property
    def metadata_index_path(self) -> str:
        """Full path to metadata index."""
        return f"{self.base_path}/{self.metadata_index_name}"

    @computed_field
    @property
    def data_index_path(self) -> str:
        """Full path to data index."""
        return f"{self.base_path}/{self.data_index_name}"


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

    # Vector Store - uses VECTOR_STORE__BASE_PATH, VECTOR_STORE__EMBEDDING_MODEL, etc.
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Using lru_cache ensures settings are only loaded once.
    """
    return Settings()
