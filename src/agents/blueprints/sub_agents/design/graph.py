"""Design sub-graph for collaborative blueprint planning."""

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.blueprints.state import BlueprintsState
from agents.blueprints.sub_agents.design.nodes import (
    DesignAgentNode,
    UpdateDesignContextNode,
)
from shared.config import get_settings


def _create_nodes(settings):
    """Instantiate all Design sub-graph nodes."""
    return {
        "design_agent": DesignAgentNode.from_settings(settings),
        "update_design_context": UpdateDesignContextNode(settings),
    }


def build_design_graph() -> CompiledStateGraph:
    """Build and compile the Design sub-graph."""
    settings = get_settings()
    nodes = _create_nodes(settings)

    workflow = StateGraph(BlueprintsState)
    for name, node in nodes.items():
        workflow.add_node(name, node)

    workflow.set_entry_point("design_agent")
    workflow.add_edge("design_agent", "update_design_context")
    workflow.add_edge("update_design_context", END)

    return workflow.compile()
