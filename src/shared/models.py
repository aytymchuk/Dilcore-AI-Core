"""Shared models used across the application."""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class LLMDecision(BaseModel, Generic[T]):
    """A generic wrapper for LLM structured outputs to ensure reasoning is provided."""

    reasoning: str = Field(
        ...,
        description="Step-by-step reasoning explaining how the decision was reached.",
    )
    decision: T = Field(
        ...,
        description="The final structured decision output.",
    )
