"""Thread API request models."""

from pydantic import BaseModel, Field


class ThreadMessageInputDto(BaseModel):
    """Input DTO for thread messages."""

    message: str = Field(
        ...,
        min_length=1,
        max_length=4000,
        description="The user message.",
    )
    file: str | None = Field(
        default=None,
        description="Base64 encoded file content. Ignored for now.",
    )
