"""LangGraph state definition for the Blueprints agent.

The state is a TypedDict that flows through every node in the graph.
"""

from __future__ import annotations

from typing import Annotated

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict


class BlueprintsState(TypedDict):
    """Base state for the Blueprints LangGraph.

    Attributes:
        messages: LangChain message history (reducer: add_messages).
        next_route: The next node to route to, determined by the supervisor.
    """

    messages: Annotated[list[BaseMessage], add_messages]
    next_route: str
