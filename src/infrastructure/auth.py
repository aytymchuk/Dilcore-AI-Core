"""Authentication dependencies using Auth0."""

from __future__ import annotations

import logging
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer
from jwt import PyJWKClient

from application.abstractions.abc_user_context_provider import AbcUserContextProvider
from application.domain.current_user import CurrentUser
from infrastructure.user_provider import set_user_id
from shared.config import Settings, get_settings

logger = logging.getLogger(__name__)

# To avoid recreating the JWK client on every request, we can cache it
_jwks_clients: dict[str, PyJWKClient] = {}


def get_jwks_client(domain: str) -> PyJWKClient:
    """Get or create a cached JWKS client for the given Auth0 domain."""
    if domain not in _jwks_clients:
        jwks_url = f"https://{domain}/.well-known/jwks.json"
        _jwks_clients[domain] = PyJWKClient(jwks_url)
    return _jwks_clients[domain]


class Auth0UserContextProvider(AbcUserContextProvider):
    """Auth0 implementation of AbcUserContextProvider."""

    def __init__(self, token: str, settings: Settings):
        self._token = token
        self.settings = settings

    def resolve_current_user(self) -> CurrentUser:
        """Verify the Auth0 token and extract user claims."""
        token = self._token
        domain = self.settings.auth0.domain
        audience = self.settings.auth0.audience

        jwks_client = get_jwks_client(domain)

        try:
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=audience,
                issuer=f"https://{domain}/",
                options={"verify_exp": True, "verify_aud": True, "verify_iss": True},
            )

            user_id = payload.get("sub", "")
            set_user_id(user_id)

            return CurrentUser(
                user_id=user_id,
                email=payload.get("email") or payload.get("https://schema.org/email"),
                full_name=payload.get("name") or payload.get("https://schema.org/name"),
            )
        except jwt.ExpiredSignatureError as e:
            logger.warning("JWT validation error: token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is not authenticated.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e
        except jwt.PyJWTError as e:
            logger.warning("JWT validation error: %s", e)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User is not authenticated.",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

    def get_user_id(self) -> str:
        """Retrieve user ID by parsing the token quickly."""
        try:
            # Skip verification as full token verification occurs in resolve_current_user
            payload = jwt.decode(self._token, options={"verify_signature": False})
            return payload.get("sub", "")
        except jwt.PyJWTError:
            from shared.constants import UNKNOWN_CONTEXT_VALUE

            return UNKNOWN_CONTEXT_VALUE


def get_oauth2_scheme() -> OAuth2AuthorizationCodeBearer:
    settings = get_settings()
    domain = settings.auth0.domain
    audience = settings.auth0.audience

    # Auth0 typical URLs, appending audience to the authorization URL is required to get a JWT instead of an opaque token
    authorization_url = f"https://{domain}/authorize?audience={audience}"
    token_url = f"https://{domain}/oauth/token"

    return OAuth2AuthorizationCodeBearer(
        authorizationUrl=authorization_url,
        tokenUrl=token_url,
    )


# Instantiate the scheme at module level
oauth2_scheme = get_oauth2_scheme()


async def verify_token(
    token: str = Depends(oauth2_scheme),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> str:
    """Verify the token is present and valid. Can be used as a simple endpoint protector."""
    provider = Auth0UserContextProvider(token=token, settings=settings)
    # resolve_current_user will raise HTTPException if invalid
    provider.resolve_current_user()
    return token


async def get_user_context_provider(
    token: str = Depends(oauth2_scheme),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> AbcUserContextProvider:
    """Dependency to provide the AbcUserContextProvider."""
    return Auth0UserContextProvider(token=token, settings=settings)


UserContextDep = Annotated[AbcUserContextProvider, Depends(get_user_context_provider)]
