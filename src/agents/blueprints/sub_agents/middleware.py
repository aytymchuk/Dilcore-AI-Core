"""Middleware for Blueprints sub-agents.

Provides reusable @after_model hooks that automatically tag AI messages
with the originating agent type, replacing manual tag_ai_messages() calls.
"""

from __future__ import annotations

from typing import Any

from langchain.agents.middleware import AgentState, after_model
from langgraph.runtime import Runtime

from agents.blueprints.constants import AgentType


def create_agent_type_tagger(agent_type: AgentType):
    """Return an @after_model middleware that stamps ``agent_type`` on every AI message.

    Usage::

        agent = create_agent(
            model=llm,
            tools=[...],
            system_prompt=PROMPT,
            middleware=[create_agent_type_tagger("ask")],
        )
    """

    @after_model
    def tag_agent_type(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        messages = state.get("messages", [])
        if not messages:
            return None

        last = messages[-1]
        if last.type == "ai":
            updated_messages = list(messages)
            new_last = last.copy()
            new_last.additional_kwargs = {**last.additional_kwargs, "agent_type": agent_type}
            updated_messages[-1] = new_last
            return {"messages": updated_messages}

        return None

    return tag_agent_type
