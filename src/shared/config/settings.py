"""Application settings using Pydantic BaseSettings."""

from functools import lru_cache

from pydantic import BaseModel, Field, SecretStr, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenRouterSettings(BaseModel):
    """OpenRouter API configuration."""

    api_key: SecretStr
    base_url: str = "https://openrouter.ai/api/v1"
    model: str = "openai/gpt-oss-20b:free"


class Auth0Settings(BaseModel):
    """Auth0 tenant and API configuration."""

    domain: str = Field(default="example.auth0.com", description="Auth0 tenant domain")
    client_id: str = Field(default="placeholder_client_id", description="Auth0 client ID for OpenAPI / Swagger UI")
    client_secret: SecretStr = Field(
        default=SecretStr("placeholder_secret"), description="Auth0 client secret for OpenAPI / Swagger UI"
    )
    audience: str = Field(default="https://api.example.com", description="Auth0 API audience identifier")


class MongoDBSettings(BaseModel):
    """MongoDB configuration for LangGraph checkpointer persistence."""

    connection_string: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection string",
    )
    db_name: str = Field(
        default="langgraph_checkpoints",
        description="Database name for checkpoint storage",
    )


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
    app_version: str = "0.0.1-dev"
    app_debug: bool = False
    log_level: str = "INFO"
    cors_origins: list[str] = Field(default=["*"], description="Allowed CORS origins")

    # OpenRouter - uses OPENROUTER__API_KEY, OPENROUTER__BASE_URL, etc.
    openrouter: OpenRouterSettings

    # Auth0 - uses AUTH0__DOMAIN, AUTH0__CLIENT_ID, etc.
    auth0: Auth0Settings | None = Field(default_factory=Auth0Settings)

    # MongoDB - uses MONGODB__CONNECTION_STRING, MONGODB__DB_NAME
    mongodb: MongoDBSettings = Field(default_factory=MongoDBSettings)

    # Vector Store - uses VECTOR_STORE__BASE_PATH, VECTOR_STORE__EMBEDDING_MODEL, etc.
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings)

    # Azure Telemetry
    azure_application_insights_connection_string: str = Field(
        default="", description="Azure Application Insights connection string for OpenTelemetry"
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Using lru_cache ensures settings are only loaded once.
    """
    return Settings()
