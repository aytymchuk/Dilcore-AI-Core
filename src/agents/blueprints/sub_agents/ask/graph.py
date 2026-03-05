"""Ask sub-graph for providing guidance and information about blueprints."""

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.blueprints.state import BlueprintsState
from agents.blueprints.sub_agents.ask.nodes import AskAgentNode
from shared.config import get_settings


def _create_nodes(settings):
    """Instantiate all Ask sub-graph nodes."""
    return {
        "ask_agent": AskAgentNode.from_settings(settings),
    }


def build_ask_graph() -> CompiledStateGraph:
    """Build and compile the Ask sub-graph."""
    settings = get_settings()
    nodes = _create_nodes(settings)

    workflow = StateGraph(BlueprintsState)
    for name, node in nodes.items():
        workflow.add_node(name, node)

    workflow.set_entry_point("ask_agent")
    workflow.add_edge("ask_agent", END)

    return workflow.compile()
