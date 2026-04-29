"""Thread response DTOs for the agent orchestration API.

Defines the response shapes returned by thread endpoints:
- MessageDto: individual message in a thread conversation.
- ThreadResponseDto: full thread state with messages.
- InterruptResponseDto: response returned when a graph interrupt is pending.
- ThreadItemDto: lightweight summary used in thread listings.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class MessageDto(BaseModel):
    """A single message exchanged within a thread."""

    id: str = Field(..., description="Stable message identifier for anchoring reasoning.")
    type: str = Field(..., description="Message role (e.g. 'human', 'ai')")
    content: str = Field(..., description="Message text content")
    agent_type: str | None = Field(
        default=None,
        description="Sub-agent that produced this message: 'ask', 'design', or 'generate'.",
    )


class ReasoningEnvelopeDto(BaseModel):
    """A contiguous reasoning envelope anchored after a message."""

    id: str = Field(..., description="Reasoning envelope identifier.")
    type: Literal["thinking", "reasoning"] = Field(..., description="Reasoning block type.")
    after_message_id: str = Field(..., description="Message id this envelope should render after.")
    sequence: int = Field(..., description="Monotonic ordering of envelopes in the thread.")
    node: str | None = Field(default=None, description="Graph node attribution when available.")
    agent_type: str | None = Field(default=None, description="Sub-agent attribution when available.")
    header: str | None = Field(default=None, description="Human-friendly envelope header for this node turn.")
    steps: list[dict] = Field(default_factory=list, description="Structured reasoning steps (step/summary/next_steps).")


class ActionRequestDto(BaseModel):
    """Mirrors ``langgraph.prebuilt.interrupt.ActionRequest``."""

    action: str = Field(..., description="Type or name of the action being requested.")
    args: dict = Field(default_factory=dict, description="Key-value arguments for the action.")


class HumanInterruptConfigDto(BaseModel):
    """Mirrors ``langgraph.prebuilt.interrupt.HumanInterruptConfig``."""

    allow_ignore: bool = Field(..., description="Whether the user can skip this step.")
    allow_respond: bool = Field(..., description="Whether the user can provide free-text feedback.")
    allow_edit: bool = Field(..., description="Whether the user can edit the proposed content.")
    allow_accept: bool = Field(..., description="Whether the user can accept/approve as-is.")


class InterruptDto(BaseModel):
    """A single pending interrupt surfaced to the client."""

    action_request: ActionRequestDto
    config: HumanInterruptConfigDto
    description: str | None = Field(
        default=None,
        description="Human-readable explanation of what input is needed.",
    )


class ThreadResponseDto(BaseModel):
    """Response DTO containing thread details."""

    id: str = Field(..., description="Unique thread identifier")
    messages: list[MessageDto] = Field(
        default_factory=list,
        description="Ordered list of messages from the thread state",
    )
    reasoning: list[ReasoningEnvelopeDto] = Field(
        default_factory=list,
        description="Ordered list of persisted reasoning envelopes for this thread.",
    )


class InterruptResponseDto(BaseModel):
    """Response returned when a graph interrupt is pending.

    Clients receiving this should render an approval / edit UI and
    call the ``/resume`` endpoint to continue execution.
    """

    id: str = Field(..., description="Unique thread identifier")
    interrupts: list[InterruptDto] = Field(
        ...,
        description="Pending interrupts that require user action.",
    )
    messages: list[MessageDto] = Field(
        default_factory=list,
        description="Messages produced before the interrupt (e.g. the presented plan).",
    )
    reasoning: list[ReasoningEnvelopeDto] = Field(
        default_factory=list,
        description="Ordered list of persisted reasoning envelopes for this thread.",
    )


class ThreadItemDto(BaseModel):
    """DTO representing a thread item in a list."""

    id: str = Field(..., description="Unique thread identifier")
    name: str = Field(..., description="Human-readable name of the thread")
