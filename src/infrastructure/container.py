"""Infrastructure dependency injection container."""

from dependency_injector import containers, providers

from infrastructure.clients.tenant_api import TenantApiClient
from infrastructure.http.request_context_accessor import RequestContextAccessTokenAccessor
from infrastructure.tenant_provider import HeaderTenantProvider
from infrastructure.tenants.current_tenant_provider import CurrentTenantProvider
from infrastructure.tracing.telemetry import setup_telemetry
from infrastructure.user_provider import ContextUserProvider
from shared.config.settings import Settings


def _api_base_url(settings: Settings) -> str:
    return str(settings.api_settings.base_url)


def _tenant_api_timeout_seconds(settings: Settings) -> float:
    return settings.api_settings.tenant_http_timeout_seconds


def _tenant_http_max_retries(settings: Settings) -> int:
    return settings.api_settings.tenant_http_max_retries


def _tenant_http_retry_base_seconds(settings: Settings) -> float:
    return settings.api_settings.tenant_http_retry_base_seconds


def _tenant_http_retry_max_delay_seconds(settings: Settings) -> float:
    return settings.api_settings.tenant_http_retry_max_delay_seconds


def _tenant_info_cache_ttl_seconds(settings: Settings) -> float:
    return settings.api_settings.tenant_info_cache_ttl_seconds


class InfrastructureContainer(containers.DeclarativeContainer):
    """Container for infrastructure layer dependencies."""

    shared = providers.DependenciesContainer()

    tenant_provider = providers.Singleton(HeaderTenantProvider)
    user_provider = providers.Singleton(ContextUserProvider)

    access_token_accessor = providers.Factory(RequestContextAccessTokenAccessor)

    api_base_url = providers.Callable(_api_base_url, shared.settings)
    tenant_api_timeout_seconds = providers.Callable(_tenant_api_timeout_seconds, shared.settings)
    tenant_http_max_retries = providers.Callable(_tenant_http_max_retries, shared.settings)
    tenant_http_retry_base_seconds = providers.Callable(_tenant_http_retry_base_seconds, shared.settings)
    tenant_http_retry_max_delay_seconds = providers.Callable(_tenant_http_retry_max_delay_seconds, shared.settings)
    tenant_info_cache_ttl_seconds = providers.Callable(_tenant_info_cache_ttl_seconds, shared.settings)

    tenant_api_client = providers.Singleton(
        TenantApiClient,
        base_url=api_base_url,
        token_accessor=access_token_accessor,
        timeout_seconds=tenant_api_timeout_seconds,
        max_retries=tenant_http_max_retries,
        retry_base_delay_seconds=tenant_http_retry_base_seconds,
        retry_max_delay_seconds=tenant_http_retry_max_delay_seconds,
    )

    current_tenant_provider = providers.Singleton(
        CurrentTenantProvider,
        api_client=tenant_api_client,
        cache_ttl_seconds=tenant_info_cache_ttl_seconds,
    )

    telemetry = providers.Resource(
        setup_telemetry,
        tenant_provider,
        user_provider,
        shared.settings,
    )
