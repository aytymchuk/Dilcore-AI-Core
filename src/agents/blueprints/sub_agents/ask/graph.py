"""Ask sub-graph for providing guidance and information about blueprints."""

from langchain.agents import create_agent
from langgraph.graph.state import CompiledStateGraph

from agents.blueprints.sub_agents.ask.prompts import ASK_SYSTEM_PROMPT
from agents.blueprints.sub_agents.ask.tools import get_blueprint_configuration_info
from infrastructure.llm import create_creative_llm
from shared.config import get_settings


def build_ask_graph() -> CompiledStateGraph:
    """Build and compile the Ask sub-graph using a ReAct agent."""
    settings = get_settings()
    llm = create_creative_llm(settings, streaming=False)

    tools = [get_blueprint_configuration_info]

    return create_agent(
        model=llm,
        tools=tools,
        system_prompt=ASK_SYSTEM_PROMPT,
    )
