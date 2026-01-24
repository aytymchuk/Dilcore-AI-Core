"""Agent module with multi-agent support."""

# Base classes
from .base import BaseAgent, StreamingAgent

# Module Builder Agent (formerly TemplateAgent)
from .core import (
    ModuleBuilderAgent,
    TemplateAgent,  # Backward compatibility alias
    create_template_agent,
)

# Persona Agent
from .persona import PersonaAgent

# Registry
from .registry import AgentRegistry

# Streaming Module Builder Agent (formerly StreamingTemplateAgent)
from .streaming import (
    StreamingModuleBuilderAgent,
    StreamingTemplateAgent,  # Backward compatibility alias
    create_streaming_template_agent,
)

__all__ = [
    # Base classes
    "BaseAgent",
    "StreamingAgent",
    # Registry
    "AgentRegistry",
    # Module Builder
    "ModuleBuilderAgent",
    "TemplateAgent",  # Backward compatibility
    "create_template_agent",
    # Streaming Module Builder
    "StreamingModuleBuilderAgent",
    "StreamingTemplateAgent",  # Backward compatibility
    "create_streaming_template_agent",
    # Persona
    "PersonaAgent",
]
