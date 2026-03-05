"""Generate sub-graph with plan-confirm-execute loop.

Flow: build_plan -> present_plan -> collect_response -[INTERRUPT]-> handle_response
      handle_response -> write_success (if confirmed)
      handle_response -> build_plan   (if corrections)

The interrupt happens inside ``collect_response`` via ``interrupt()`` using
the structured ``HumanInterrupt`` payload.  The caller resumes with
``Command(resume=<HumanResponse>)``.
"""

from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.blueprints.state import BlueprintsState
from agents.blueprints.sub_agents.generate.nodes import (
    BuildPlanNode,
    CollectUserResponseNode,
    HandleResponseNode,
    PresentPlanNode,
    WriteSuccessNode,
)
from shared.config import get_settings


def _should_loop(state: BlueprintsState) -> str:
    """Route after handle_response: loop back or finish."""
    if state.get("generation_plan_confirmed", False):
        return "write_success"
    return "build_plan"


def _create_nodes(settings):
    """Instantiate all Generate sub-graph nodes."""
    return {
        "build_plan": BuildPlanNode(settings),
        "present_plan": PresentPlanNode(),
        "collect_response": CollectUserResponseNode(),
        "handle_response": HandleResponseNode(settings),
        "write_success": WriteSuccessNode(),
    }


def build_generate_graph() -> CompiledStateGraph:
    """Build and compile the Generate sub-graph with HITL confirmation loop."""
    settings = get_settings()
    nodes = _create_nodes(settings)

    workflow = StateGraph(BlueprintsState)
    for name, node in nodes.items():
        workflow.add_node(name, node)

    workflow.set_entry_point("build_plan")
    workflow.add_edge("build_plan", "present_plan")
    workflow.add_edge("present_plan", "collect_response")
    workflow.add_edge("collect_response", "handle_response")
    workflow.add_conditional_edges("handle_response", _should_loop, ["write_success", "build_plan"])
    workflow.add_edge("write_success", END)

    return workflow.compile()
