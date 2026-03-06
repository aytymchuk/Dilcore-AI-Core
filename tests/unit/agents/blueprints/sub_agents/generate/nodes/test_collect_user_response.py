"""Unit tests for the CollectUserResponseNode."""

from unittest.mock import patch

import pytest
from langchain_core.messages import HumanMessage

from agents.blueprints.models import PlanAction
from agents.blueprints.sub_agents.generate.nodes.collect_user_response import (
    CollectUserResponseNode,
)


@pytest.mark.asyncio
async def test_collect_user_response_accept():
    """CollectUserResponseNode should set plan confirmed if user accepts."""
    node = CollectUserResponseNode()
    state = {
        "generation_plan": [PlanAction(action="create", target="X", description="D")],
        "messages": [],
    }

    # mock interrupt to return "accept" response
    # interrupt returns a list of responses, we take the first one
    mock_response = [{"type": "accept", "args": None}]

    with patch(
        "agents.blueprints.sub_agents.generate.nodes.collect_user_response.interrupt", return_value=mock_response
    ):
        result = await node(state)

        assert result == {"generation_plan_confirmed": True}


@pytest.mark.asyncio
async def test_collect_user_response_edit():
    """CollectUserResponseNode should return a HumanMessage if user edits."""
    node = CollectUserResponseNode()
    state = {"generation_plan": [], "messages": []}

    mock_response = [{"type": "edit", "args": "New plan description"}]

    with patch(
        "agents.blueprints.sub_agents.generate.nodes.collect_user_response.interrupt", return_value=mock_response
    ):
        result = await node(state)

        assert "messages" in result
        assert isinstance(result["messages"][0], HumanMessage)
        assert result["messages"][0].content == "New plan description"


@pytest.mark.asyncio
async def test_collect_user_response_text_response():
    """CollectUserResponseNode should return a HumanMessage if user provides free-text feedback."""
    node = CollectUserResponseNode()
    state = {"generation_plan": [], "messages": []}

    mock_response = [{"type": "response", "args": "Make it better"}]

    with patch(
        "agents.blueprints.sub_agents.generate.nodes.collect_user_response.interrupt", return_value=mock_response
    ):
        result = await node(state)

        assert "messages" in result
        assert isinstance(result["messages"][0], HumanMessage)
        assert result["messages"][0].content == "Make it better"
