"""Blueprints LangGraph — Supervisor wiring.

Compiles a routing supervisor graph that connects to:
- intent resolution
- guidance ("ask" sub-graph)
- generation ("generate" sub-graph)
"""

from __future__ import annotations

import logging

from langgraph.graph import END, START, StateGraph

from agents.blueprints.nodes import (
    ASK_ROUTE,
    GENERATE_ROUTE,
    IDENTIFY_INTENT_ROUTE,
    IdentifyIntentNode,
    SupervisorNode,
)
from agents.blueprints.state import BlueprintsState
from agents.blueprints.sub_agents.ask.graph import build_ask_graph
from agents.blueprints.sub_agents.generate.graph import build_generate_graph
from infrastructure.checkpoint.document_checkpointer import get_checkpointer
from infrastructure.llm import create_llm
from shared.config import Settings

logger = logging.getLogger(__name__)


class BlueprintsGraph:
    """Encapsulates the compiled Blueprints Supervisor Graph.

    Lifecycle:
        - Created once per application.
        - Uses MongoDB checkpointer for thread state persistence.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm = create_llm(settings, streaming=False)
        self._graph = self._build_graph()

    def _build_graph(self):
        """Build and compile the Supervisor LangGraph."""
        builder = StateGraph(BlueprintsState)

        builder.add_node("supervisor", SupervisorNode(self._llm))
        builder.add_node(ASK_ROUTE, build_ask_graph())
        builder.add_node(IDENTIFY_INTENT_ROUTE, IdentifyIntentNode())
        builder.add_node(GENERATE_ROUTE, build_generate_graph())

        builder.add_edge(ASK_ROUTE, END)
        builder.add_edge(IDENTIFY_INTENT_ROUTE, END)
        builder.add_edge(GENERATE_ROUTE, END)

        builder.add_edge(START, "supervisor")

        return builder.compile(checkpointer=get_checkpointer())

    async def ainvoke(self, state: dict, config: dict | None = None) -> dict:
        """Invoke the graph with state."""
        return await self._graph.ainvoke(state, config)


# ---------------------------------------------------------------------------
# Lazy entrypoint for LangGraph Studio / CLI
# ---------------------------------------------------------------------------
_graph = None


def __getattr__(name: str):
    """Lazily construct the compiled graph on first access."""
    global _graph  # noqa: PLW0603
    if name == "graph":
        if _graph is None:
            from shared.config import get_settings

            _graph = BlueprintsGraph(get_settings())._graph
        return _graph
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
