"""Unit tests for the UpdateDesignContextNode."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from agents.blueprints.sub_agents.design.nodes.update_design_context import (
    UpdateDesignContextNode,
)


@pytest.fixture
def mock_llm():
    """Create a mock LLM."""
    llm = AsyncMock()
    llm.ainvoke.return_value = AIMessage(content="Updated summary: User wants a CRM.")
    return llm


@pytest.mark.asyncio
async def test_update_design_context_summarizes(mock_llm):
    """UpdateDesignContextNode should summarize the conversation."""
    mock_settings = MagicMock()

    with patch("agents.blueprints.sub_agents.design.nodes.update_design_context.create_llm") as mock_create:
        mock_create.return_value = mock_llm

        node = UpdateDesignContextNode(mock_settings)
        state = {
            "messages": [
                HumanMessage(content="I want to build a CRM"),
                AIMessage(content="Sure, what entities?"),
            ],
            "design_context": "Initial context",
        }

        result = await node(state)

        assert "design_context" in result
        assert result["design_context"] == "Updated summary: User wants a CRM."
        assert mock_llm.ainvoke.called
        mock_create.assert_called_once_with(mock_settings)
