"""Users controller."""

from fastapi import APIRouter, HTTPException, status

from application.domain.current_user import CurrentUser
from infrastructure.auth import CurrentUserResolverDep
from shared.exceptions import AuthenticationError

users_router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@users_router.get("/current")
async def get_current_user_endpoint(resolver: CurrentUserResolverDep) -> CurrentUser:
    """Retrieve the current authenticated user's claims.

    Includes userId, email, and fullName.
    """
    try:
        return resolver.resolve_current_user()
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
