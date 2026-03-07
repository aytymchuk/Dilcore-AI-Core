"""Users controller."""

from fastapi import APIRouter

from api.controllers.auth_dependencies import UserContextDep
from application.domain.current_user import CurrentUser

users_router = APIRouter(prefix="/api/v1/users", tags=["Users"])


@users_router.get("/current")
async def get_current_user_endpoint(resolver: UserContextDep) -> CurrentUser:
    """Retrieve the current authenticated user's claims.

    Includes userId, email, and fullName.
    """
    return resolver.resolve_current_user()
