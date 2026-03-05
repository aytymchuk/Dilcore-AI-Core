"""Pydantic models for the Blueprints agent graph.

Provides strongly typed schemas for generation plans and confirmation
classification, replacing loose ``dict`` / raw-string patterns.

The ``ActionRequest``, ``HumanInterruptConfig``, ``HumanInterrupt``, and
``HumanResponse`` TypedDicts are local equivalents of the same-named types
in ``langgraph.prebuilt.interrupt`` (which are deprecated in the installed
version).  Defining them here avoids the deprecation warning and removes
the dependency on an unstable import path.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field
from typing_extensions import TypedDict

# ---------------------------------------------------------------------------
# HITL interrupt types (mirrors langgraph.prebuilt.interrupt)
# ---------------------------------------------------------------------------


class ActionRequest(TypedDict):
    """Action the graph is requesting from the human."""

    action: str
    args: dict


class HumanInterruptConfig(TypedDict):
    """Controls which response types are allowed for a given interrupt."""

    allow_ignore: bool
    allow_respond: bool
    allow_edit: bool
    allow_accept: bool


class HumanInterrupt(TypedDict):
    """Full interrupt payload passed to ``interrupt()``."""

    action_request: ActionRequest
    config: HumanInterruptConfig
    description: str | None


class HumanResponse(TypedDict):
    """Value sent back via ``Command(resume=...)``."""

    type: Literal["accept", "ignore", "response", "edit"]
    args: None | str | ActionRequest


class PlanAction(BaseModel):
    """A single step in a generation plan."""

    action: str = Field(
        ...,
        description="Operation type (e.g. 'create_entity', 'add_field', 'link_entities').",
    )
    target: str = Field(
        ...,
        description="What the action applies to (e.g. 'Customer', 'Deal.amount').",
    )
    description: str = Field(
        ...,
        description="Brief human-readable description of what this action does.",
    )
    params: dict[str, Any] = Field(
        default_factory=dict,
        description="Parameters for the action.",
    )


class GenerationPlan(BaseModel):
    """Wrapper returned by the planner LLM via structured output."""

    actions: list[PlanAction] = Field(
        ...,
        description="Ordered list of actions to execute.",
    )


class ConfirmationClassification(BaseModel):
    """Result of classifying the user's response to a presented plan."""

    decision: Literal["confirmed", "corrections"] = Field(
        ...,
        description="Whether the user confirmed the plan or requested corrections.",
    )
