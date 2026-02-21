"""Streaming event schemas for SSE-based template generation."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from .response import TemplateResponse


class StreamEventType(StrEnum):
    """Types of streaming events during template generation."""

    THINKING = "thinking"
    CONTENT = "content"
    TEMPLATE = "template"
    ERROR = "error"
    DONE = "done"


class StreamEvent(BaseModel):
    """A single event in the SSE stream."""

    event_type: StreamEventType = Field(..., description="Type of streaming event")
    data: Any = Field(..., description="Event payload — string for chunks, dict for template")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Event timestamp",
    )


class StreamingTemplateResponse(BaseModel):
    """Final response containing template and explanation."""

    template: TemplateResponse = Field(..., description="The generated template")
    explanation: str = Field(
        ...,
        description="AI-generated explanation of the template design decisions",
    )
