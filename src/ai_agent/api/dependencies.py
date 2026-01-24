"""FastAPI dependencies for dependency injection."""

from typing import Annotated

from fastapi import Depends

from ai_agent.agent import (
    StreamingTemplateAgent,
    TemplateAgent,
    create_streaming_template_agent,
    create_template_agent,
)
from ai_agent.config import Settings, get_settings

# Type aliases for dependency injection
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_agent(settings: SettingsDep) -> TemplateAgent:
    """Get the TemplateAgent instance.

    Args:
        settings: Application settings.

    Returns:
        The configured TemplateAgent.
    """
    return create_template_agent(settings)


AgentDep = Annotated[TemplateAgent, Depends(get_agent)]


def get_streaming_agent(settings: SettingsDep) -> StreamingTemplateAgent:
    """Get the StreamingTemplateAgent instance.

    Args:
        settings: Application settings.

    Returns:
        The configured StreamingTemplateAgent.
    """
    return create_streaming_template_agent(settings)


StreamingAgentDep = Annotated[StreamingTemplateAgent, Depends(get_streaming_agent)]
