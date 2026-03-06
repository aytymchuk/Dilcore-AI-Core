"""Unit tests for the WriteSuccessNode."""

import pytest
from langchain_core.messages import AIMessage

from agents.blueprints.constants import GENERATE_AGENT
from agents.blueprints.models import PlanAction
from agents.blueprints.sub_agents.generate.nodes.write_success import WriteSuccessNode


@pytest.mark.asyncio
async def test_write_success_node_returns_success_msg():
    """WriteSuccessNode should return a success message."""
    node = WriteSuccessNode()
    plan = [PlanAction(action="create_entity", target="Customer", description="Create customer entity")]
    state = {"generation_plan": plan, "messages": []}

    result = await node(state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    msg = result["messages"][0]
    assert isinstance(msg, AIMessage)
    assert "planned and simulated" in msg.content
    assert "skeleton" in msg.content
    assert "1 action(s)" in msg.content
    assert msg.additional_kwargs.get("agent_type") == GENERATE_AGENT
