"""Ask sub-graph for providing guidance and information about blueprints."""

from langchain_core.messages import SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.blueprints.state import BlueprintsState
from agents.blueprints.sub_agents.ask.prompts import ASK_SYSTEM_PROMPT
from infrastructure.llm import create_llm
from shared.config import get_settings


async def ask_node(state: BlueprintsState) -> dict:
    """Answers user queries about blueprints."""
    settings = get_settings()
    llm = create_llm(settings, streaming=False)

    # Prepend the system prompt to the conversation history
    messages = [SystemMessage(content=ASK_SYSTEM_PROMPT)] + state["messages"]

    response = await llm.ainvoke(messages)
    return {"messages": [response]}


def build_ask_graph() -> CompiledStateGraph:
    """Build and compile the Ask sub-graph."""
    workflow = StateGraph(BlueprintsState)
    workflow.add_node("ask", ask_node)
    workflow.set_entry_point("ask")
    workflow.add_edge("ask", END)

    return workflow.compile()
