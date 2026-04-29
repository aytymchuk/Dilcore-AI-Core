"""OpenAPI schema generation and documentation routes."""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse
from scalar_fastapi import get_scalar_api_reference
from scalar_fastapi.scalar_fastapi import DocumentDownloadType

from api.schemas.sse import blueprint_sse_event_json_schema
from shared.config import get_settings

logger = logging.getLogger(__name__)

_SCALAR_CDN = "https://cdn.jsdelivr.net/npm/@scalar/api-reference"


def _rewrite_json_schema_defs_refs(obj: Any) -> Any:
    """Turn Pydantic ``#/$defs/X`` references into ``#/components/schemas/X``."""
    if isinstance(obj, dict):
        return {
            k: (
                v.replace("#/$defs/", "#/components/schemas/")
                if k == "$ref" and isinstance(v, str)
                else _rewrite_json_schema_defs_refs(v)
            )
            for k, v in obj.items()
        }
    if isinstance(obj, list):
        return [_rewrite_json_schema_defs_refs(i) for i in obj]
    return obj


def _register_blueprint_sse_event_schemas(openapi_schema: dict[str, Any]) -> None:
    """Merge Blueprints SSE ``data:`` JSON union into ``components.schemas``."""
    raw = blueprint_sse_event_json_schema()
    defs = raw.pop("$defs", {})
    components = openapi_schema.setdefault("components", {}).setdefault("schemas", {})
    for name, subschema in defs.items():
        components[name] = _rewrite_json_schema_defs_refs(subschema)
    components["BlueprintSseEvent"] = _rewrite_json_schema_defs_refs(raw)


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

    _register_blueprint_sse_event_schemas(openapi_schema)

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

        scalar_result = get_scalar_api_reference(
            openapi_url=spec_url,
            title=f"{settings.application.name} - API Reference",
            scalar_js_url=_SCALAR_CDN,
            document_download_type=DocumentDownloadType.BOTH,
            authentication=authentication or {},
        )

        # scalar-fastapi normally returns an HTMLResponse, but tests may monkeypatch it to a str.
        response = HTMLResponse(scalar_result) if isinstance(scalar_result, str) else scalar_result

        if spec_url and getattr(response, "body", None):
            marker = '<div id="app"></div>'
            body = bytes(response.body)
            response.body = body.replace(
                marker.encode(),
                (
                    (
                        marker
                        + f"""
        <div style="position:fixed;right:12px;top:12px;z-index:9999;font-family:ui-sans-serif,system-ui,-apple-system;">
            <a href="{spec_url}" target="_blank" rel="noopener noreferrer"
               style="display:inline-block;padding:8px 10px;border-radius:8px;background:rgba(0,0,0,0.65);color:#fff;text-decoration:none;font-size:12px;backdrop-filter:saturate(180%) blur(8px);">
                OpenAPI spec
            </a>
        </div>
"""
                    ).encode()
                ),
            )
            # Keep Content-Length consistent with our mutated body (uvicorn enforces this).
            response.headers["content-length"] = str(len(response.body))

        return response
