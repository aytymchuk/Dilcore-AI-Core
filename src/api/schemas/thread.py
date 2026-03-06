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
    def _validate_and_normalize(self) -> ResumeInputDto:
        # 1. Normalize message-only input
        if self.type is None:
            if not self.message:
                raise ValueError("Either 'type' or 'message' must be provided.")
            self.type = "response"
            self.args = self.message

        # 2. Validate combinations
        if self.type == "edit":
            if not isinstance(self.args, ActionRequestDto):
                raise ValueError("For 'edit' response, 'args' must be an ActionRequest object.")
        elif self.type == "response":
            if self.message:
                self.args = self.message
                self.message = None
            if self.args is not None and not isinstance(self.args, str):
                raise ValueError("For 'response', 'args' must be a string or null.")
        elif self.type in ("accept", "ignore") and self.args is not None:
            raise ValueError(f"Response type '{self.type}' cannot have 'args'.")

        # 3. Ensure mutual exclusivity of message and type (when type was explicitly set)
        # Actually, if type was None, we just set it. If it was provided, message should be null.
        if self.message and self.type != "response":
            # This is a bit strict, but follows the instruction "when type is set message must be null"
            raise ValueError("Provide either 'message' (for plain text response) OR 'type' + 'args'.")

        return self
