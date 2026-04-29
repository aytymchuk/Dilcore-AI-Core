"""Unit tests for the SupervisorNode."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from langgraph.types import Command

from agents.blueprints.constants import (
    ASK_ROUTE,
    DESIGN_ROUTE,
    GENERATE_ROUTE,
    IDENTIFY_INTENT_ROUTE,
)
from agents.blueprints.nodes.supervisor import SupervisorDecision, SupervisorNode
from shared.exceptions.base import LLMProviderError
from shared.models import LLMDecision
from shared.reasoning import ReasoningBuffer, reset_reasoning_buffer, set_reasoning_buffer, with_reasoning_node


@pytest.fixture
def mock_llm():
    """Create a mock LLM."""
    return MagicMock()


@pytest.mark.asyncio
async def test_supervisor_routes_to_ask(mock_llm):
    """Supervisor should route to ASK_ROUTE based on LLM decision."""
    decision = SupervisorDecision(next_route=ASK_ROUTE)
    llm_output = LLMDecision(decision=decision, reasoning="User wants to ask something.")

    # mock with_structured_output return value
    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = llm_output
    mock_llm.with_structured_output.return_value = mock_structured_llm

    node = SupervisorNode(mock_llm)
    state = {"messages": [], "current_phase": ""}

    buf = ReasoningBuffer(thread_id="t1", anchor_message_id="m-0", sequence_base=0)
    token = set_reasoning_buffer(buf)
    try:
        result = await with_reasoning_node("supervisor", node)(state)
    finally:
        reset_reasoning_buffer(token)

    assert isinstance(result, Command)
    assert result.goto == ASK_ROUTE
    assert result.update["current_phase"] == ASK_ROUTE
    assert buf.envelopes()[0].header == "Understanding what you want to do"
    assert any("blueprints" in (s.content or "").lower() for s in buf.envelopes()[0].steps)
    assert any(s.kind == "summary" and "Next step:" in (s.content or "") for s in buf.envelopes()[0].steps)


@pytest.mark.asyncio
async def test_supervisor_routes_to_design(mock_llm):
    """Supervisor should route to DESIGN_ROUTE based on LLM decision."""
    decision = SupervisorDecision(next_route=DESIGN_ROUTE)
    llm_output = LLMDecision(decision=decision, reasoning="User wants to design.")

    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = llm_output
    mock_llm.with_structured_output.return_value = mock_structured_llm

    node = SupervisorNode(mock_llm)
    state = {"messages": [], "current_phase": ""}

    result = await node(state)

    assert result.goto == DESIGN_ROUTE


@pytest.mark.asyncio
async def test_supervisor_routes_to_generate(mock_llm):
    """Supervisor should route to GENERATE_ROUTE based on LLM decision."""
    decision = SupervisorDecision(next_route=GENERATE_ROUTE)
    llm_output = LLMDecision(decision=decision, reasoning="User wants to generate.")

    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = llm_output
    mock_llm.with_structured_output.return_value = mock_structured_llm

    node = SupervisorNode(mock_llm)
    state = {"messages": [], "current_phase": "design"}

    result = await node(state)

    assert result.goto == GENERATE_ROUTE


@pytest.mark.asyncio
async def test_supervisor_raises_llm_provider_error_on_failure(mock_llm):
    """Supervisor should raise LLMProviderError on LLM error."""

    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.side_effect = Exception("LLM Error")
    mock_llm.with_structured_output.return_value = mock_structured_llm

    node = SupervisorNode(mock_llm)
    state = {"messages": [], "current_phase": ""}

    with pytest.raises(LLMProviderError, match="Failed to generate supervisor decision: LLM Error"):
        await node(state)


@pytest.mark.asyncio
async def test_supervisor_rejects_invalid_route(mock_llm):
    """Supervisor should route to IDENTIFY_INTENT_ROUTE if LLM returns invalid route."""
    # invalid route (not in ALL_ROUTES)
    decision = MagicMock()
    decision.next_route = "invalid_route"
    llm_output = LLMDecision(decision=decision, reasoning="Garbage output.")

    mock_structured_llm = AsyncMock()
    mock_structured_llm.ainvoke.return_value = llm_output
    mock_llm.with_structured_output.return_value = mock_structured_llm

    node = SupervisorNode(mock_llm)
    state = {"messages": [], "current_phase": ""}

    buf = ReasoningBuffer(thread_id="t1", anchor_message_id="m-0", sequence_base=0)
    token = set_reasoning_buffer(buf)
    try:
        result = await with_reasoning_node("supervisor", node)(state)
    finally:
        reset_reasoning_buffer(token)

    assert result.goto == IDENTIFY_INTENT_ROUTE
    assert any(s.status == "skipped" and "available" in (s.content or "").lower() for s in buf.envelopes()[0].steps)
