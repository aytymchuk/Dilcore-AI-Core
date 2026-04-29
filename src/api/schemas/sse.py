"""OpenAPI / documentation models for Blueprints SSE ``data:`` JSON payloads.

Runtime streaming is implemented in ``application.services.blueprints_service``;
these Pydantic models mirror that contract for schema generation.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field, TypeAdapter

from api.schemas.response import InterruptDto, MessageDto, ReasoningEnvelopeDto

# ---------------------------------------------------------------------------
# Per-category payloads (discriminated by ``category``)
# ---------------------------------------------------------------------------


class SseThinkingEvent(BaseModel):
    """Model reasoning / extended-thinking deltas (provider blocks and streamed assistant text)."""

    category: Literal["thinking"] = "thinking"
    type: Literal["thinking", "reasoning"] = Field(
        ...,
        description="Normalized reasoning block type for compatibility.",
    )
    content: str = Field(..., description="Reasoning or thinking text delta.")
    kind: Literal["step", "summary", "next_steps"] | None = Field(
        default=None,
        description="Optional structured kind for the emitted reasoning fragment.",
    )
    status: Literal["running", "completed", "failed", "skipped"] | None = Field(
        default=None,
        description="Optional status for the emitted reasoning fragment.",
    )
    after_message_id: str | None = Field(default=None, description="Message id this reasoning fragment follows.")
    sequence: int | None = Field(default=None, description="Envelope sequence this fragment belongs to.")
    node: str | None = Field(default=None, description="Graph node attribution when available.")
    agent_type: str | None = Field(default=None, description="Sub-agent attribution when available.")
    phase: str | None = Field(
        default=None,
        description="Coarse graph phase for routing/sub-agent progress (LangGraph node completion).",
    )


class SseDataEvent(BaseModel):
    """Terminal success payload with full message list."""

    category: Literal["data"] = "data"
    thread_id: str = Field(..., description="Thread identifier.")
    messages: list[MessageDto] = Field(
        default_factory=list,
        description="Ordered messages after this run.",
    )
    reasoning: list[ReasoningEnvelopeDto] = Field(
        default_factory=list,
        description="Ordered list of persisted reasoning envelopes for this thread.",
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
    reasoning: list[ReasoningEnvelopeDto] = Field(
        default_factory=list,
        description="Ordered list of persisted reasoning envelopes for this thread.",
    )


class SseErrorEvent(BaseModel):
    """Stream-level error (still SSE, not RFC 7807)."""

    category: Literal["error"] = "error"
    detail: str = Field(..., description="Error description.")


BlueprintSseEvent = Annotated[
    SseThinkingEvent | SseDataEvent | SseInterruptEvent | SseErrorEvent,
    Field(discriminator="category"),
]


def blueprint_sse_event_json_schema() -> dict:
    """JSON Schema for the union (includes ``$defs`` with ``#/$defs/...`` refs)."""
    return TypeAdapter(BlueprintSseEvent).json_schema()
