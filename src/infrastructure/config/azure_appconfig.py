"""Azure App Configuration settings source for Pydantic.

Fetches the AIAgent JSON configuration from Azure App Config
by key ``AIAgent`` and label matching the ``ENVIRONMENT`` env var.
"""

import json
import logging
import os
from typing import Any

from azure.appconfiguration import AzureAppConfigurationClient
from azure.identity import DefaultAzureCredential
from pydantic_settings import PydanticBaseSettingsSource

logger = logging.getLogger(__name__)

_APP_CONFIG_KEY = "AIAgent"


class AzureAppConfigSettingsSource(PydanticBaseSettingsSource):
    """A custom settings source that loads configuration from Azure App Configuration.

    Fetches a single JSON blob stored under the key ``AIAgent`` with
    a label equal to the ``ENVIRONMENT`` env var (e.g. ``Development``).
    The JSON structure must match the ``AIAgent`` section of ``appsettings.json``.
    """

    def get_field_value(self, field, field_name: str) -> tuple[Any, str, bool]:
        """Not used — we fetch all values at once in ``__call__``."""
        return None, field_name, False

    def prepare_field_value(self, field_name: str, field, value: Any, value_is_complex: bool) -> Any:
        """Not used — values are returned as-is."""
        return value

    def __call__(self) -> dict[str, Any]:
        """Fetch the AIAgent configuration from Azure App Configuration.

        Returns a dict matching the PascalCase JSON structure that Pydantic
        will map via field aliases (e.g. ``ApplicationSettings``, ``OpenRouterSettings``).
        """
        endpoint = os.getenv("AZURE_APPCONFIG_ENDPOINT")
        if not endpoint:
            logger.debug("AZURE_APPCONFIG_ENDPOINT not set, skipping Azure App Config source.")
            return {}

        environment = os.getenv("ENVIRONMENT", "Development")
        logger.info(
            "Loading configuration from Azure App Config: endpoint=%s, key=%s, label=%s",
            endpoint,
            _APP_CONFIG_KEY,
            environment,
        )

        try:
            credential = DefaultAzureCredential()
            client = AzureAppConfigurationClient(endpoint, credential)

            setting = client.get_configuration_setting(key=_APP_CONFIG_KEY, label=environment)

            if not setting or not setting.value:
                logger.warning("Key '%s' with label '%s' returned empty value.", _APP_CONFIG_KEY, environment)
                return {}

            config: dict[str, Any] = json.loads(setting.value)
            logger.info(
                "Successfully loaded %d top-level keys from App Config key '%s'.",
                len(config),
                _APP_CONFIG_KEY,
            )
            logger.debug("Loaded config sections: %s", list(config.keys()))
            return config

        except Exception:
            logger.exception("Failed to load configuration from Azure App Configuration.")
            return {}
