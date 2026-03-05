"""LangGraph state definition for the Blueprints agent.

The state is a TypedDict that flows through every node in the graph.
"""

from __future__ import annotations

from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict

from agents.blueprints.constants import PhaseType
from agents.blueprints.models import PlanAction


class BlueprintsState(TypedDict):
    """State for the Blueprints LangGraph.

    Attributes:
        messages: LangChain message history (reducer: add_messages).
        current_phase: Active mode — "ask", "design", "generate", or "".
        design_context: LLM-generated summary of accumulated design decisions.
        generation_plan: Ordered list of planned generation actions.
        generation_plan_confirmed: Whether the user has confirmed the plan.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    current_phase: PhaseType
    design_context: str
    generation_plan: list[PlanAction]
    generation_plan_confirmed: bool
