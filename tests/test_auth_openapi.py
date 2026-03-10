"""Regression tests for auth OpenAPI integration."""

from fastapi import FastAPI, Security
from fastapi.security import OAuth2AuthorizationCodeBearer


def test_auth_scheme_is_oauth2_authorization_code_bearer() -> None:
    """AUTH_SCHEME must be a concrete OAuth2 dependency for OpenAPI introspection."""
    from infrastructure.auth import AUTH_SCHEME, get_oauth2_scheme

    assert isinstance(AUTH_SCHEME, OAuth2AuthorizationCodeBearer)
    assert isinstance(get_oauth2_scheme(), OAuth2AuthorizationCodeBearer)


def test_openapi_contains_oauth2_security_scheme() -> None:
    """Endpoints protected with AUTH_SCHEME should emit OAuth2 OpenAPI metadata."""
    from infrastructure.auth import AUTH_SCHEME

    app = FastAPI()

    @app.get("/secure")
    async def secure(_: str = Security(AUTH_SCHEME)):
        return {"ok": True}

    schema = app.openapi()

    assert "components" in schema
    assert "securitySchemes" in schema["components"]
    assert "OAuth2AuthorizationCodeBearer" in schema["components"]["securitySchemes"]

    operation = schema["paths"]["/secure"]["get"]
    assert operation["security"] == [{"OAuth2AuthorizationCodeBearer": []}]
