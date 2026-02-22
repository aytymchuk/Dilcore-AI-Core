"""Blueprints LangGraph — Supervisor wiring.

Compiles a routing supervisor graph that connects to:
- intent resolution
- guidance ("ask" sub-graph)
- generation ("generate" sub-graph)
"""

import logging
from typing import Literal

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
from infrastructure.llm import create_llm
from shared.config import Settings, get_settings

RouteNames = Literal["ask", "identify_intent", "generate"]

logger = logging.getLogger(__name__)


# Compile sub-graphs
ask_graph = build_ask_graph()
generate_graph = build_generate_graph()


class BlueprintsGraph:
    """Encapsulates the compiled Blueprints Supervisor Graph.

    Lifecycle:
        - Created once per application.
        - The supervisor itself is stateless (no checkpointer allocated).
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm = create_llm(settings, streaming=False)
        self._graph = self._build_graph()

    async def _route(self, state: BlueprintsState) -> RouteNames:
        """Conditional edge returning the route determined by the supervisor node."""
        return state["next_route"]  # type: ignore

    def _build_graph(self):
        """Build and compile the Supervisor LangGraph."""
        builder = StateGraph(BlueprintsState)

        # Add the nodes/sub-graphs
        builder.add_node("supervisor", SupervisorNode(self._llm))
        builder.add_node(ASK_ROUTE, ask_graph)
        builder.add_node(IDENTIFY_INTENT_ROUTE, IdentifyIntentNode())
        builder.add_node(GENERATE_ROUTE, generate_graph)

        builder.add_edge(ASK_ROUTE, END)
        builder.add_edge(IDENTIFY_INTENT_ROUTE, END)
        builder.add_edge(GENERATE_ROUTE, END)

        builder.add_edge(START, "supervisor")

        # Routing edge
        builder.add_conditional_edges(
            "supervisor",
            self._route,
            {
                ASK_ROUTE: ASK_ROUTE,
                IDENTIFY_INTENT_ROUTE: IDENTIFY_INTENT_ROUTE,
                GENERATE_ROUTE: GENERATE_ROUTE,
            },
        )

        # The supervisor is stateless (no checkpointer passed here)
        return builder.compile()

    async def ainvoke(self, state: dict, config: dict | None = None) -> dict:
        """Invoke the graph with state."""
        return await self._graph.ainvoke(state, config)


# Expose compiled StateGraph for LangGraph Studio/CLI
graph = BlueprintsGraph(get_settings())._graph
