"""Thread response DTOs for the agent orchestration API.

Defines the response shapes returned by thread endpoints:
- MessageDto: individual message in a thread conversation.
- ThreadResponseDto: full thread state with messages.
- ThreadItemDto: lightweight summary used in thread listings.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MessageDto(BaseModel):
    """A single message exchanged within a thread."""

    type: str = Field(..., description="Message role (e.g. 'human', 'ai')")
    content: str = Field(..., description="Message text content")


class ThreadResponseDto(BaseModel):
    """Response DTO containing thread details."""

    id: str = Field(..., description="Unique thread identifier")
    messages: list[MessageDto] = Field(
        default_factory=list,
        description="Ordered list of messages from the thread state",
    )


class ThreadItemDto(BaseModel):
    """DTO representing a thread item in a list."""

    id: str = Field(..., description="Unique thread identifier")
    name: str = Field(..., description="Human-readable name of the thread")
