"""Unit tests for the PresentPlanNode."""

import pytest
from langchain_core.messages import AIMessage

from agents.blueprints.models import PlanAction
from agents.blueprints.sub_agents.generate.nodes.present_plan import PresentPlanNode


@pytest.mark.asyncio
async def test_present_plan_node_formats_plan():
    """PresentPlanNode should format the plan into an AIMessage."""
    node = PresentPlanNode()
    plan = [
        PlanAction(action="create_entity", target="Customer", description="Create customer entity"),
        PlanAction(action="add_field", target="Customer.name", description="Add name field"),
    ]
    state = {"generation_plan": plan, "messages": []}

    result = await node(state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    msg = result["messages"][0]
    assert isinstance(msg, AIMessage)
    assert "create_entity" in msg.content
    assert "Customer" in msg.content
    assert "add_field" in msg.content
    assert "customer entity" in msg.content
    assert "confirm" in msg.content.lower()


@pytest.mark.asyncio
async def test_present_plan_node_handles_empty_plan():
    """PresentPlanNode should handle an empty plan gracefully."""
    node = PresentPlanNode()
    state = {"generation_plan": [], "messages": []}

    result = await node(state)

    assert "messages" in result
    assert "generation plan" in result["messages"][0].content.lower()
