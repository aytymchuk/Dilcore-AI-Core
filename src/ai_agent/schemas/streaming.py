"""Streaming event schemas for SSE-based template generation."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .response import TemplateResponse


class StreamEventType(str, Enum):
    """Types of streaming events during template generation."""

    THINKING = "thinking"  # Thinking/reasoning content chunk (if model supports)
    CONTENT = "content"  # Main content chunk (non-thinking)
    TEMPLATE = "template"  # Final template JSON with explanation
    ERROR = "error"  # Error event
    DONE = "done"  # Stream completed


class StreamEvent(BaseModel):
    """A single event in the SSE stream."""

    event_type: StreamEventType = Field(..., description="Type of streaming event")
    data: Any = Field(..., description="Event payload - string for chunks, dict for template")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Event timestamp",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "event_type": "content",
                    "data": "Analyzing your request...",
                    "timestamp": "2026-01-15T00:15:00Z",
                },
                {
                    "event_type": "thinking",
                    "data": "Let me think about the structure...",
                    "timestamp": "2026-01-15T00:15:01Z",
                },
            ]
        }
    }


class StreamingTemplateResponse(BaseModel):
    """Final response containing template and explanation."""

    template: TemplateResponse = Field(..., description="The generated template")
    explanation: str = Field(
        ...,
        description="AI-generated explanation of the template design decisions",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "template": {
                        "template_id": "usr-reg-001",
                        "template_name": "User Registration Form",
                        "description": "Template for collecting user registration data",
                        "status": "draft",
                        "metadata": {
                            "version": "1.0.0",
                            "author": "AI Agent",
                            "tags": ["user", "registration"],
                        },
                        "sections": [],
                    },
                    "explanation": (
                        "This template uses a simple structure with "
                        "essential fields for user registration."
                    ),
                }
            ]
        }
    }
