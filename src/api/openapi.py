"""OpenAPI schema generation and documentation routes."""

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from scalar_fastapi import get_scalar_api_reference

from shared.config import get_settings


def custom_openapi(app: FastAPI) -> dict[str, Any]:
    """Generate custom OpenAPI schema with enhanced error documentation."""
    if app.openapi_schema:
        return app.openapi_schema

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

    @app.get("/scalar", include_in_schema=False)
    async def scalar_docs():
        return get_scalar_api_reference(
            openapi_url=app.openapi_url,
            title=f"{settings.application.name} - API Reference",
            authentication={
                "preferredSecurityScheme": "OAuth2AuthorizationCodeBearer",
                "securitySchemes": {
                    "OAuth2AuthorizationCodeBearer": {
                        "flows": {
                            "authorizationCode": {
                                "x-scalar-client-id": settings.authentication.auth0.client_id,
                                "clientSecret": settings.authentication.auth0.client_secret.get_secret_value(),
                                "selectedScopes": ["openid", "profile", "email"],
                            }
                        }
                    }
                },
            },
        )
