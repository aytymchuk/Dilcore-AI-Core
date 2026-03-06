"""Integration tests for AI agent (BlueprintsGraph) module.

Includes both Docker-based tests (real MongoDB) and mocked tests (MemorySaver).
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver

from agents.blueprints.constants import ASK_ROUTE, IDENTIFY_INTENT_ROUTE


@pytest.fixture
def mock_settings():
    """Create mock settings for testing."""
    env_vars = {
        "OPENROUTER__API_KEY": "test-api-key",
        "OPENROUTER__BASE_URL": "https://openrouter.ai/api/v1",
        "OPENROUTER__MODEL": "openai/gpt-oss-20b:free",
    }
    with patch.dict(os.environ, env_vars, clear=False):
        from shared.config.settings import Settings, get_settings

        get_settings.cache_clear()
        yield Settings()
        get_settings.cache_clear()


@pytest.fixture
def mock_checkpointer():
    """Mock get_checkpointer to return a MemorySaver for non-Docker tests."""
    with patch("agents.blueprints.graph.get_checkpointer") as mock_get:
        mock_get.return_value = MemorySaver()
        yield mock_get


class TestBlueprintsGraphInitialization:
    """Basic initialization tests."""

    @pytest.mark.integration
    def test_graph_initializes_with_settings(self, mock_settings, mock_checkpointer) -> None:
        """BlueprintsGraph should initialize with correct settings."""
        with (
            patch("infrastructure.llm.client.ChatOpenAI"),
            patch("infrastructure.llm.client.OpenAIEmbeddings"),
            patch("store.vector.faiss_store.FAISS"),
        ):
            from agents.blueprints.graph import BlueprintsGraph

            graph = BlueprintsGraph(mock_settings)

            assert graph._settings == mock_settings
            assert graph._llm is not None


class TestBlueprintsGraphFlow:
    """Tests for graph routing and execution flow using mocked LLM."""

    @pytest.mark.asyncio
    async def test_full_graph_turn_identify_intent(self, mock_settings, mock_checkpointer):
        """Test a full turn that routes to IdentifyIntentNode."""
        from langgraph.types import Command

        from agents.blueprints.graph import BlueprintsGraph

        mock_llm = MagicMock()

        with (
            patch("agents.blueprints.graph.create_llm", return_value=mock_llm),
            patch("agents.blueprints.sub_agents.react_agent_node.create_creative_llm", return_value=mock_llm),
            patch("agents.blueprints.sub_agents.generate.nodes.build_plan.create_llm", return_value=mock_llm),
            patch("agents.blueprints.sub_agents.generate.nodes.handle_response.create_llm", return_value=mock_llm),
            patch("agents.blueprints.sub_agents.design.nodes.update_design_context.create_llm", return_value=mock_llm),
            patch("infrastructure.llm.client.OpenAIEmbeddings"),
            patch("store.vector.faiss_store.FAISS"),
            patch("agents.blueprints.nodes.supervisor.SupervisorNode.__call__") as mock_sup_call,
        ):
            mock_sup_call.return_value = Command(
                goto=IDENTIFY_INTENT_ROUTE, update={"current_phase": IDENTIFY_INTENT_ROUTE}
            )

            graph = BlueprintsGraph(mock_settings)
            state = {"messages": [HumanMessage(content="Hello")]}
            config = {"configurable": {"thread_id": "test-thread-id-1"}}

            result = await graph.ainvoke(state, config)

            assert "messages" in result
            assert len(result["messages"]) >= 2
            assert "clarify" in result["messages"][-1].content

    @pytest.mark.asyncio
    async def test_graph_routes_to_ask_agent(self, mock_settings, mock_checkpointer):
        """Test that graph routes to Ask sub-agent correctly."""
        from langgraph.types import Command

        from agents.blueprints.graph import BlueprintsGraph

        mock_llm = MagicMock()

        with (
            patch("agents.blueprints.graph.create_llm", return_value=mock_llm),
            patch("agents.blueprints.sub_agents.react_agent_node.create_creative_llm", return_value=mock_llm),
            patch("agents.blueprints.sub_agents.generate.nodes.build_plan.create_llm", return_value=mock_llm),
            patch("agents.blueprints.sub_agents.generate.nodes.handle_response.create_llm", return_value=mock_llm),
            patch("agents.blueprints.sub_agents.design.nodes.update_design_context.create_llm", return_value=mock_llm),
            patch("infrastructure.llm.client.OpenAIEmbeddings"),
            patch("store.vector.faiss_store.FAISS"),
            patch("agents.blueprints.nodes.supervisor.SupervisorNode.__call__") as mock_sup_call,
            patch("agents.blueprints.sub_agents.ask.nodes.ask_agent.AskAgentNode.__call__") as mock_ask_call,
        ):
            mock_sup_call.return_value = Command(goto=ASK_ROUTE, update={"current_phase": ASK_ROUTE})
            mock_ask_call.return_value = {"messages": [AIMessage(content="I am the ask agent.")]}

            graph = BlueprintsGraph(mock_settings)
            state = {"messages": [HumanMessage(content="What are blueprints?")]}
            config = {"configurable": {"thread_id": "test-thread-id-2"}}

            result = await graph.ainvoke(state, config)

            assert result["current_phase"] == ASK_ROUTE
            assert "I am the ask agent." in result["messages"][-1].content
