"""Thread API request models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from api.schemas.response import ActionRequestDto


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


class ResumeInputDto(BaseModel):
    """Input DTO for resuming a thread from an interrupt.

    Supports two modes:

    1. **Structured** — provide ``type`` with optional ``args``.
    2. **Plain text** — provide only ``message``; it is normalised to
       ``type="response", args=<message>``.
    """

    type: Literal["accept", "ignore", "response", "edit"] | None = Field(
        default=None,
        description=(
            "Response type: 'accept' to approve, 'ignore' to skip, "
            "'response' for free-text feedback, 'edit' to modify the action."
        ),
    )
    args: str | ActionRequestDto | None = Field(
        default=None,
        description="Payload for the response — free-text string or an ActionRequest for edits.",
    )
    message: str | None = Field(
        default=None,
        max_length=4000,
        description="Plain-text fallback. When provided without ``type``, treated as type='response'.",
    )

    @model_validator(mode="after")
    def _require_type_or_message(self) -> ResumeInputDto:
        if self.type is None and not self.message:
            raise ValueError("Either 'type' or 'message' must be provided.")
        return self
