"""Domain model for the authenticated user."""

from pydantic import BaseModel, EmailStr


class CurrentUser(BaseModel):
    """Strongly typed, immutable model representing the current authenticated user."""

    model_config = {"frozen": True}

    user_id: str
    email: EmailStr | None = None
    full_name: str | None = None
