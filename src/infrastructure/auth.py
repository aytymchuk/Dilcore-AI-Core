"""Authentication dependencies using Auth0."""

from __future__ import annotations

import logging
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.concurrency import run_in_threadpool
from fastapi.security import OAuth2AuthorizationCodeBearer
from jwt import PyJWKClient

from application.abstractions.abc_user_context_provider import (
    AbcCurrentUserResolver,
    AbcUserContextProvider,
    AbcUserIdProvider,
)
from application.domain.current_user import CurrentUser
from infrastructure.user_provider import set_user_id
from shared.config import Settings, get_settings
from shared.exceptions import AuthenticationError, ConfigurationError

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
        if settings.auth0 is None:
            raise ConfigurationError("Auth0 settings are missing.")
        self._token = token
        self.settings = settings
        self._resolved_user: CurrentUser | None = None

    def get_user_id(self) -> str:
        """Parse token to get user ID without verification.

        WARNING: Use only for optional ambient context lookup.
        """
        try:
            payload = jwt.decode(self._token, options={"verify_signature": False})
            return str(payload.get("sub", "UNKNOWN"))
        except jwt.PyJWTError:
            return "UNKNOWN"

    def resolve_current_user(self) -> CurrentUser:
        """Verify the Auth0 token and extract user claims."""
        if self._resolved_user:
            return self._resolved_user

        if self.settings.auth0 is None:
            raise ConfigurationError("Auth0 settings are missing.")

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

            user_id = payload.get("sub")
            if not user_id:
                logger.warning("JWT validation error: missing 'sub' claim in token")
                raise AuthenticationError("Invalid token: missing subject.")
            set_user_id(user_id)

            self._resolved_user = CurrentUser(
                user_id=user_id,
                email=payload.get("email") or payload.get("https://schema.org/email"),
                full_name=payload.get("name") or payload.get("https://schema.org/name"),
            )
            return self._resolved_user
        except jwt.ExpiredSignatureError as e:
            logger.warning("JWT validation error: token has expired")
            raise AuthenticationError("Token has expired.") from e
        except jwt.PyJWTError as e:
            logger.warning("JWT validation error [%s]: %s", type(e).__name__, e)
            raise AuthenticationError("Invalid token.") from e


def get_oauth2_scheme() -> OAuth2AuthorizationCodeBearer:
    settings = get_settings()
    if settings.auth0 is None:
        # Fallback for local development
        return OAuth2AuthorizationCodeBearer(
            authorizationUrl="/authorize",
            tokenUrl="/token",
        )
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
AUTH_SCHEME = oauth2_scheme


async def get_active_user_context_provider(
    token: Annotated[str, Security(AUTH_SCHEME)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AbcCurrentUserResolver:
    """Dependency to provide the AbcCurrentUserResolver (e.g. Auth0)."""
    return Auth0UserContextProvider(token, settings)


async def verify_token(
    user_resolver: Annotated[AbcCurrentUserResolver, Depends(get_active_user_context_provider)],
) -> None:
    """Verify the token is present and valid. Can be used as a simple endpoint protector."""
    try:
        # resolve_current_user is synchronous and blocks the event loop;
        # offload it to a threadpool.
        current_user = await run_in_threadpool(user_resolver.resolve_current_user)

        # Re-populate the context for the current async thread/task
        # so that get_user_context_provider() can retrieve it.
        set_user_id(current_user.user_id)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


async def get_user_context_provider(
    _verify: Annotated[None, Depends(verify_token)],
) -> AbcUserIdProvider:
    """Dependency to provide the AbcUserIdProvider (Ambient Context)."""
    from infrastructure.user_provider import ContextUserProvider

    return ContextUserProvider()


UserContextDep = Annotated[AbcUserIdProvider, Depends(get_user_context_provider)]
CurrentUserResolverDep = Annotated[AbcCurrentUserResolver, Depends(get_active_user_context_provider)]
