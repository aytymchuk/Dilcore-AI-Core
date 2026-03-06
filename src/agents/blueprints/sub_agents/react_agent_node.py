"""Generic ReAct agent node for Blueprints sub-graphs.

Replaces per-sub-agent boilerplate (AskAgentNode, DesignAgentNode, etc.)
with a single configurable class that differs only by prompt, tools, and
agent type.
"""

from __future__ import annotations

from typing import Self

from langchain.agents import create_agent
from langgraph.graph.state import CompiledStateGraph

from agents.blueprints.state import BlueprintsState
from agents.blueprints.sub_agents.middleware import create_agent_type_tagger
from infrastructure.llm import create_creative_llm
from shared.config import Settings


class ReActAgentNode:
    """Runs an inner ReAct agent and returns only the newly produced messages."""

    def __init__(self, agent: CompiledStateGraph) -> None:
        self._agent = agent

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        system_prompt: str,
        tools: list,
        agent_type: str,
    ) -> Self:
        llm = create_creative_llm(settings, streaming=False)
        agent = create_agent(
            model=llm,
            tools=tools,
            system_prompt=system_prompt,
            middleware=[create_agent_type_tagger(agent_type)],
        )
        return cls(agent)

    async def __call__(self, state: BlueprintsState) -> dict:
        result = await self._agent.ainvoke({"messages": state["messages"]})
        input_count = len(state["messages"])
        return {"messages": result.get("messages", [])[input_count:]}
