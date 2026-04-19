"""OpenAPI / documentation models for Blueprints SSE ``data:`` JSON payloads.

Runtime streaming is implemented in ``application.services.blueprints_service``;
these Pydantic models mirror that contract for schema generation.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter

from api.schemas.response import InterruptDto, MessageDto

# ---------------------------------------------------------------------------
# Per-category payloads (discriminated by ``category``)
# ---------------------------------------------------------------------------


class SseStatusEvent(BaseModel):
    """High-level step (routing or sub-phase)."""

    category: Literal["status"] = "status"
    message: str = Field(..., description="User-facing status line.")
    phase: str = Field(
        ...,
        description="Coarse phase, e.g. routing, ask, design, generate, identify_intent.",
    )


class SseThinkingEvent(BaseModel):
    """Model reasoning / extended-thinking delta when the provider exposes it."""

    category: Literal["thinking"] = "thinking"
    content: str = Field(..., description="Reasoning or thinking text delta.")


class SseDeltaEvent(BaseModel):
    """Streamed assistant text token(s)."""

    category: Literal["delta"] = "delta"
    content: str = Field(..., description="Visible assistant text delta.")
    agent_type: str | None = Field(
        default=None,
        description="Sub-agent when tagged: ask, design, or generate.",
    )


class SseDataEvent(BaseModel):
    """Terminal success payload with full message list."""

    category: Literal["data"] = "data"
    thread_id: str = Field(..., description="Thread identifier.")
    messages: list[MessageDto] = Field(
        default_factory=list,
        description="Ordered messages after this run.",
    )


class SseInterruptEvent(BaseModel):
    """Human-in-the-loop pause (same shape as non-stream interrupt response plus category)."""

    category: Literal["interrupt"] = "interrupt"
    id: str = Field(..., description="Thread identifier.")
    interrupts: list[InterruptDto] = Field(
        ...,
        description="Pending interrupts requiring user action.",
    )
    messages: list[MessageDto] = Field(
        default_factory=list,
        description="Messages produced before the interrupt.",
    )


class SseErrorEvent(BaseModel):
    """Stream-level error (still SSE, not RFC 7807)."""

    category: Literal["error"] = "error"
    detail: str = Field(..., description="Error description.")


BlueprintSseEvent = Annotated[
    SseStatusEvent | SseThinkingEvent | SseDeltaEvent | SseDataEvent | SseInterruptEvent | SseErrorEvent,
    Field(discriminator="category"),
]


def blueprint_sse_event_json_schema() -> dict:
    """JSON Schema for the union (includes ``$defs`` with ``#/$defs/...`` refs)."""
    return TypeAdapter(BlueprintSseEvent).json_schema()
