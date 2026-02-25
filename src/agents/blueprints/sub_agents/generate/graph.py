"""Generate sub-graph for creating blueprints."""

from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.blueprints.state import BlueprintsState


async def dummy_generate_node(state: BlueprintsState) -> dict:
    """Dummy generation node."""
    message = AIMessage(content="Generation process is resolved and steps will be implemented soon.")
    return {"messages": [message]}


def build_generate_graph() -> CompiledStateGraph:
    """Build and compile the Generate sub-graph.

    No checkpointer is set here — the parent supervisor graph provides one,
    and sub-graphs inherit it automatically.
    """
    workflow = StateGraph(BlueprintsState)
    workflow.add_node("generate", dummy_generate_node)
    workflow.set_entry_point("generate")
    workflow.add_edge("generate", END)
    return workflow.compile()
