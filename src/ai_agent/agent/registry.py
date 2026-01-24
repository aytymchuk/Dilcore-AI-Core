"""Agent registry for managing available agents."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ai_agent.config import Settings

    from .base import BaseAgent


class AgentRegistry:
    """Registry for managing available agents.

    Provides a central location to register agent classes and retrieve
    singleton instances of agents by their type identifier.

    Example:
        >>> @AgentRegistry.register("my-agent")
        ... class MyAgent(BaseAgent):
        ...     pass
        >>> agent = AgentRegistry.get_agent("my-agent", settings)
    """

    _agents: dict[str, type[BaseAgent]] = {}
    _instances: dict[str, BaseAgent] = {}

    @classmethod
    def register(cls, agent_type: str):
        """Decorator to register an agent class.

        Args:
            agent_type: Unique identifier for this agent type.

        Returns:
            Decorator function that registers the agent class.

        Example:
            >>> @AgentRegistry.register("module-builder")
            ... class ModuleBuilderAgent(BaseAgent):
            ...     pass
        """

        def wrapper(agent_class: type[BaseAgent]) -> type[BaseAgent]:
            cls._agents[agent_type] = agent_class
            return agent_class

        return wrapper

    @classmethod
    def get_agent(cls, agent_type: str, settings: Settings) -> BaseAgent:
        """Get or create an agent instance.

        Maintains singleton instances per agent type to ensure
        consistent state across requests.

        Args:
            agent_type: The type identifier of the agent to retrieve.
            settings: Application settings for agent initialization.

        Returns:
            The agent instance.

        Raises:
            ValueError: If the agent type is not registered.
        """
        if agent_type not in cls._instances:
            if agent_type not in cls._agents:
                raise ValueError(f"Unknown agent type: {agent_type}")
            cls._instances[agent_type] = cls._agents[agent_type](settings)
        return cls._instances[agent_type]

    @classmethod
    def list_agents(cls) -> list[str]:
        """List all registered agent types.

        Returns:
            List of registered agent type identifiers.
        """
        return list(cls._agents.keys())

    @classmethod
    def is_registered(cls, agent_type: str) -> bool:
        """Check if an agent type is registered.

        Args:
            agent_type: The type identifier to check.

        Returns:
            True if the agent type is registered, False otherwise.
        """
        return agent_type in cls._agents

    @classmethod
    def clear_instances(cls) -> None:
        """Clear all cached agent instances.

        Useful for testing or when settings change.
        """
        cls._instances.clear()
