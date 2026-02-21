"""API request models."""

from pydantic import BaseModel, Field


class GenerateRequest(BaseModel):
    """Request model for template generation."""

    prompt: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="User prompt describing the template to generate",
        examples=["Create a user registration form template"],
    )
