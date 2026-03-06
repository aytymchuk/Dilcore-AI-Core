"""Ask sub-graph for providing guidance and information about blueprints."""

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.blueprints.state import BlueprintsState
from agents.blueprints.sub_agents.ask.nodes import AskAgentNode
from shared.config import Settings


def build_ask_graph(settings: Settings) -> CompiledStateGraph:
    """Build and compile the Ask sub-graph."""
    from typing import Any

    nodes: dict[str, Any] = {
        "ask_agent": AskAgentNode.from_settings(settings),
    }

    workflow = StateGraph(BlueprintsState)
    for name, node in nodes.items():
        workflow.add_node(name, node)

    workflow.set_entry_point("ask_agent")
    workflow.add_edge("ask_agent", END)

    return workflow.compile()
