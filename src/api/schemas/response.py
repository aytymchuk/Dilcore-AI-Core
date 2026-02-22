"""Static JSON response structure for template generation."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ThreadResponseDto(BaseModel):
    """Response DTO containing thread details."""

    id: str = Field(..., description="Unique thread identifier")
    messages: list[Any] = Field(
        default_factory=list,
        description="List of messages from the thread state",
    )


class ThreadItemDto(BaseModel):
    """DTO representing a thread item in a list."""

    id: str = Field(..., description="Unique thread identifier")
    name: str = Field(..., description="Human-readable name of the thread")
