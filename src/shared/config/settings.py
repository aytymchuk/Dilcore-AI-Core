"""Application settings using Pydantic BaseSettings."""

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, SecretStr, computed_field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

# Load .env file into os.environ so that AzureAppConfigSettingsSource can read it via os.getenv
load_dotenv()


class ApplicationSettings(BaseModel):
    """Application-level settings (maps to AIAgent.ApplicationSettings in JSON)."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(default="AI Template Agent", alias="Name")
    version: str = Field(default="0.0.1-dev", alias="Version")
    debug: bool = Field(default=False, alias="Debug")
    log_level: str = Field(default="INFO", alias="LogLevel")
    cors_origins: list[str] = Field(default=["*"], alias="CorsOrigins")


class OpenRouterSettings(BaseModel):
    """OpenRouter API configuration (maps to AIAgent.OpenRouterSettings in JSON)."""

    model_config = ConfigDict(populate_by_name=True)

    api_key: SecretStr = Field(alias="ApiKey")
    base_url: str = Field(default="https://openrouter.ai/api/v1", alias="BaseUrl")
    model: str = Field(default="openai/gpt-oss-20b:free", alias="Model")


class Auth0Settings(BaseModel):
    """Auth0 tenant and API configuration (maps to AIAgent.AuthenticationSettings.Auth0 in JSON)."""

    model_config = ConfigDict(populate_by_name=True)

    domain: str = Field(default="example.auth0.com", alias="Domain", description="Auth0 tenant domain")
    client_id: str = Field(
        default="placeholder_client_id", alias="ClientId", description="Auth0 client ID for OpenAPI / Swagger UI"
    )
    client_secret: SecretStr = Field(
        default=SecretStr("placeholder_secret"),
        alias="ClientSecret",
        description="Auth0 client secret for OpenAPI / Swagger UI",
    )
    audience: str = Field(
        default="https://api.example.com", alias="Audience", description="Auth0 API audience identifier"
    )


class AuthenticationSettings(BaseModel):
    """Wrapper for authentication providers (maps to AIAgent.AuthenticationSettings in JSON)."""

    model_config = ConfigDict(populate_by_name=True)

    auth0: Auth0Settings | None = Field(default=None, alias="Auth0")


class MongoDBSettings(BaseModel):
    """MongoDB configuration for LangGraph checkpointer persistence (maps to AIAgent.MongoDbSettings in JSON)."""

    model_config = ConfigDict(populate_by_name=True)

    connection_string: str = Field(
        default="mongodb://localhost:27017",
        alias="ConnectionString",
        description="MongoDB connection string",
    )
    db_name: str = Field(
        default="langgraph_checkpoints",
        alias="DbName",
        description="Database name for checkpoint storage",
    )


class VectorStoreSettings(BaseModel):
    """FAISS vector store configuration (maps to AIAgent.VectorStoreSettings in JSON)."""

    model_config = ConfigDict(populate_by_name=True)

    provider: str = Field(default="faiss", alias="Provider", description="Vector store provider (faiss)")
    base_path: str = Field(
        default="./data/vector_store",
        alias="BasePath",
        description="Base path for FAISS indices",
    )
    metadata_index_name: str = Field(
        default="metadata_index",
        alias="MetadataIndexName",
        description="Name of the metadata index (forms, views, entities, etc.)",
    )
    data_index_name: str = Field(
        default="data_index",
        alias="DataIndexName",
        description="Name of the data index (actual records)",
    )
    embedding_model: str = Field(
        default="openai/text-embedding-3-small",
        alias="EmbeddingModel",
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


class AzureTelemetrySettings(BaseModel):
    """Azure telemetry configuration (maps to AIAgent.AzureTelemetry in JSON)."""

    model_config = ConfigDict(populate_by_name=True)

    application_insights_connection_string: str = Field(
        default="",
        alias="ApplicationInsightsConnectionString",
        description="Azure Application Insights connection string for OpenTelemetry",
    )


class LangSmithSettings(BaseModel):
    """LangSmith/LangChain tracing configuration (maps to AIAgent.LangSmithSettings in JSON)."""

    model_config = ConfigDict(populate_by_name=True)

    tracing_enabled: bool = Field(default=False, alias="TracingEnabled")
    endpoint: str = Field(default="https://api.smith.langchain.com", alias="Endpoint")
    api_key: SecretStr = Field(default=SecretStr(""), alias="ApiKey")
    project: str = Field(default="Dilcore AI Agent", alias="Project")


class ApiSettings(BaseModel):
    """API-related settings loaded from Azure App Configuration."""

    model_config = ConfigDict(populate_by_name=True)

    base_url: HttpUrl = Field(default="http://localhost:8080", alias="BaseUrl", validate_default=True)
    tenant_http_timeout_seconds: float = Field(
        default=30.0,
        alias="TenantHttpTimeoutSeconds",
        description="HTTP read timeout for platform tenant API (get current tenant)",
        ge=1.0,
        le=120.0,
    )
    tenant_http_max_retries: int = Field(
        default=3,
        alias="TenantHttpMaxRetries",
        description="Retry count for transient tenant API errors (timeouts, connection issues, 5xx, 429)",
        ge=0,
        le=10,
    )
    tenant_http_retry_base_seconds: float = Field(
        default=0.25,
        alias="TenantHttpRetryBaseSeconds",
        description="Initial backoff delay for tenant API retries (exponential)",
        ge=0.05,
        le=10.0,
    )
    tenant_http_retry_max_delay_seconds: float = Field(
        default=8.0,
        alias="TenantHttpRetryMaxDelaySeconds",
        description="Backoff cap between tenant API retries",
        ge=0.5,
        le=60.0,
    )
    tenant_info_cache_ttl_seconds: float = Field(
        default=3600.0,
        alias="TenantInfoCacheTtlSeconds",
        description="TTL for in-process tenant info cache (CurrentTenantProvider)",
        ge=60.0,
        le=86400.0,
    )


class Settings(BaseSettings):
    """Application settings loaded from environment variables or Azure App Configuration.

    Settings can be loaded from:
    1. Constructor arguments (highest priority)
    2. Environment variables
    3. .env file
    4. Azure App Configuration (key=AIAgent, label=ENVIRONMENT)
    5. File secrets (lowest priority)
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        populate_by_name=True,
    )

    # Bootstrap settings (always from env, not from JSON)
    environment: str = Field(default="Development", description="Environment name used as App Config label")
    azure_appconfig_endpoint: str = Field(default="", description="Azure App Configuration endpoint URL")

    # Application settings (maps to AIAgent.ApplicationSettings)
    application: ApplicationSettings = Field(default_factory=ApplicationSettings, alias="ApplicationSettings")

    # OpenRouter (maps to AIAgent.OpenRouterSettings)
    openrouter: OpenRouterSettings = Field(alias="OpenRouterSettings")

    # Authentication (maps to AIAgent.AuthenticationSettings)
    authentication: AuthenticationSettings = Field(
        default_factory=AuthenticationSettings, alias="AuthenticationSettings"
    )

    # MongoDB (maps to AIAgent.MongoDbSettings)
    mongodb: MongoDBSettings = Field(default_factory=MongoDBSettings, alias="MongoDbSettings")

    # Vector Store (maps to AIAgent.VectorStoreSettings)
    vector_store: VectorStoreSettings = Field(default_factory=VectorStoreSettings, alias="VectorStoreSettings")

    # Azure Telemetry (maps to AIAgent.AzureTelemetry)
    azure_telemetry: AzureTelemetrySettings = Field(default_factory=AzureTelemetrySettings, alias="AzureTelemetry")

    # LangSmith (maps to AIAgent.LangSmithSettings)
    langsmith: LangSmithSettings = Field(default_factory=LangSmithSettings, alias="LangSmithSettings")

    # API Settings (maps to AIAgent.ApiSettings loaded from Azure App Configuration)
    api_settings: ApiSettings = Field(default_factory=ApiSettings, alias="ApiSettings")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customise settings sources to include Azure App Configuration."""
        from infrastructure.config.azure_appconfig import AzureAppConfigSettingsSource

        init = init_settings()
        env = env_settings()
        dotenv = dotenv_settings()

        endpoint = (
            init.get("azure_appconfig_endpoint")
            or env.get("azure_appconfig_endpoint")
            or dotenv.get("azure_appconfig_endpoint")
        )
        environment = init.get("environment") or env.get("environment") or dotenv.get("environment")

        return (
            init_settings,
            env_settings,
            dotenv_settings,
            AzureAppConfigSettingsSource(settings_cls, endpoint=endpoint, environment=environment),
            file_secret_settings,
        )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Using lru_cache ensures settings are only loaded once.
    """
    return Settings()
