"""Unit tests for the IdentifyIntentNode."""

import pytest
from langchain_core.messages import AIMessage

from agents.blueprints.nodes.identify_intent import IdentifyIntentNode


@pytest.mark.asyncio
async def test_identify_intent_node_returns_clarification():
    """IdentifyIntentNode should return a clarification message."""
    node = IdentifyIntentNode()
    state = {"messages": []}

    result = await node(state)

    assert "messages" in result
    assert len(result["messages"]) == 1
    assert isinstance(result["messages"][0], AIMessage)
    assert "clarify" in result["messages"][0].content
    assert "understand blueprints" in result["messages"][0].content
