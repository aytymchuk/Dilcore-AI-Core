"""OpenAPI schema generation and documentation routes."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from scalar_fastapi import get_scalar_api_reference

from shared.config import get_settings

logger = logging.getLogger(__name__)

_SCALAR_CDN = "https://cdn.jsdelivr.net/npm/@scalar/api-reference"


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    """Generate custom OpenAPI schema with enhanced error documentation."""
    if app.openapi_schema:
        return app.openapi_schema

    logger.debug("Building OpenAPI schema (cached on app after first build)")
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    openapi_schema.setdefault("components", {}).setdefault("schemas", {})["ProblemDetails"] = {
        "type": "object",
        "required": ["type", "title", "status", "detail", "instance"],
        "properties": {
            "type": {"type": "string", "example": "https://api.dilcore.ai/problems/validation-error"},
            "title": {"type": "string", "example": "Validation Error"},
            "status": {"type": "integer", "minimum": 400, "maximum": 599, "example": 400},
            "detail": {"type": "string", "example": "The request body contains invalid data"},
            "instance": {"type": "string", "example": "/api/v1/blueprints/start"},
        },
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def setup_openapi(app: FastAPI) -> None:
    """Configure OpenAPI schema and documentation routes."""
    app.openapi = lambda: custom_openapi(app)  # noqa: E731

    settings = get_settings()

    logger.info(
        "API documentation: GET /scalar (loads Scalar from %s); OpenAPI JSON at %s",
        _SCALAR_CDN,
        app.openapi_url or "(disabled)",
    )

    @app.get("/scalar", include_in_schema=False)
    async def scalar_docs(request: Request):
        spec_url = str(request.base_url).rstrip("/") + app.openapi_url if app.openapi_url else None
        logger.debug(
            "GET /scalar client=%s x_forwarded_host=%s openapi_spec_url=%s",
            getattr(request.client, "host", None),
            request.headers.get("x-forwarded-host"),
            spec_url,
        )

        auth0 = settings.authentication.auth0
        authentication = None
        if auth0 is not None:
            authentication = {
                "preferredSecurityScheme": "OAuth2AuthorizationCodeBearer",
                "securitySchemes": {
                    "OAuth2AuthorizationCodeBearer": {
                        "flows": {
                            "authorizationCode": {
                                "x-scalar-client-id": auth0.client_id,
                                "clientSecret": auth0.client_secret.get_secret_value(),
                                "selectedScopes": ["openid", "profile", "email"],
                            }
                        }
                    }
                },
            }

        return get_scalar_api_reference(
            openapi_url=spec_url,
            title=f"{settings.application.name} - API Reference",
            scalar_js_url=_SCALAR_CDN,
            authentication=authentication or {},
        )
