"""Generate sub-graph for creating blueprints."""

from langchain_core.messages import AIMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.blueprints.state import BlueprintsState
from infrastructure.checkpoint.document_checkpointer import get_checkpointer


async def dummy_generate_node(state: BlueprintsState) -> dict:
    """Dummy generation node."""
    message = AIMessage(content="Generation process is resolved and steps will be implemented soon.")
    return {"messages": [message]}


def build_generate_graph() -> CompiledStateGraph:
    """Build and compile the Generate sub-graph."""
    workflow = StateGraph(BlueprintsState)
    workflow.add_node("generate", dummy_generate_node)
    workflow.set_entry_point("generate")
    workflow.add_edge("generate", END)

    # We use the MongoDB checkpointer here so this subgraph
    # can remember thread state across restarts.
    checkpointer = get_checkpointer()
    return workflow.compile(checkpointer=checkpointer)
