"""Base agent classes and interfaces for multi-agent architecture."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from langchain_openai import ChatOpenAI

from ai_agent.config import Settings


class BaseAgent(ABC):
    """Abstract base class for all AI agents.

    Provides common infrastructure for agent implementations including
    LLM initialization and settings management.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the agent with application settings.

        Args:
            settings: Application settings containing LLM and vector store config.
        """
        self._settings = settings
        self._llm = self._create_llm()

    def _create_llm(self) -> ChatOpenAI:
        """Create and configure the LLM instance.

        Returns:
            Configured ChatOpenAI instance.
        """
        return ChatOpenAI(
            api_key=self._settings.openrouter.api_key.get_secret_value(),
            base_url=self._settings.openrouter.base_url,
            model=self._settings.openrouter.model,
            temperature=0,
        )

    @abstractmethod
    async def process(self, request: Any) -> Any:
        """Process a request and return a response.

        Args:
            request: The request to process (agent-specific type).

        Returns:
            The processed response (agent-specific type).
        """
        pass

    @property
    @abstractmethod
    def agent_type(self) -> str:
        """Return the agent type identifier.

        Returns:
            String identifier for this agent type (e.g., 'module-builder', 'persona').
        """
        pass


class StreamingAgent(BaseAgent):
    """Base class for agents that support streaming responses.

    Extends BaseAgent with streaming capability for real-time response generation.
    """

    @abstractmethod
    async def process_stream(self, request: Any) -> AsyncGenerator[Any, None]:
        """Process a request and stream the response.

        Args:
            request: The request to process (agent-specific type).

        Yields:
            Response chunks as they become available.
        """
        pass
