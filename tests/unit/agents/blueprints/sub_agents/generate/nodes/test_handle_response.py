"""Unit tests for the HandleResponseNode."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_core.messages import HumanMessage

from agents.blueprints.models import ConfirmationClassification
from agents.blueprints.sub_agents.generate.nodes.handle_response import HandleResponseNode
from shared.models import LLMDecision


@pytest.fixture
def mock_llm():
    """Create a mock LLM with configured structured output."""
    llm = MagicMock()
    structured_llm = AsyncMock()
    llm.with_structured_output.return_value = structured_llm
    return llm


@pytest.mark.asyncio
async def test_handle_response_confirmed_via_state():
    """HandleResponseNode should return immediately if plan already confirmed in state."""
    mock_settings = MagicMock()
    with patch("agents.blueprints.sub_agents.generate.nodes.handle_response.create_llm"):
        node = HandleResponseNode(mock_settings)
        state = {"generation_plan_confirmed": True, "messages": []}

        result = await node(state)

        assert result == {}


@pytest.mark.asyncio
async def test_handle_response_classifies_confirmed(mock_llm):
    """HandleResponseNode should classify "confirmed" from LLM output."""
    mock_settings = MagicMock()
    decision = ConfirmationClassification(decision="confirmed")
    llm_output = LLMDecision(decision=decision, reasoning="User said yes.")

    mock_llm.with_structured_output().ainvoke.return_value = llm_output

    with patch("agents.blueprints.sub_agents.generate.nodes.handle_response.create_llm", return_value=mock_llm):
        node = HandleResponseNode(mock_settings)
        state = {
            "generation_plan_confirmed": False,
            "messages": [HumanMessage(content="Looks good, proceed.")],
        }

        result = await node(state)

        assert result == {"generation_plan_confirmed": True}


@pytest.mark.asyncio
async def test_handle_response_classifies_corrections(mock_llm):
    """HandleResponseNode should classify "corrections" from LLM output."""
    mock_settings = MagicMock()
    decision = ConfirmationClassification(decision="corrections")
    llm_output = LLMDecision(decision=decision, reasoning="User wants changes.")

    mock_llm.with_structured_output().ainvoke.return_value = llm_output

    with patch("agents.blueprints.sub_agents.generate.nodes.handle_response.create_llm", return_value=mock_llm):
        node = HandleResponseNode(mock_settings)
        state = {
            "generation_plan_confirmed": False,
            "messages": [HumanMessage(content="Wait, add one more field.")],
        }

        result = await node(state)

        assert result == {"generation_plan_confirmed": False}


@pytest.mark.asyncio
async def test_handle_response_fallback_on_error(mock_llm):
    """HandleResponseNode should fallback to corrections on LLM error."""
    mock_settings = MagicMock()
    mock_llm.with_structured_output().ainvoke.side_effect = Exception("LLM Error")

    with patch("agents.blueprints.sub_agents.generate.nodes.handle_response.create_llm", return_value=mock_llm):
        node = HandleResponseNode(mock_settings)
        state = {
            "generation_plan_confirmed": False,
            "messages": [HumanMessage(content="Yes please.")],
        }

        result = await node(state)

        assert result == {"generation_plan_confirmed": False}
