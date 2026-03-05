"""Ask agent node — runs the inner ReAct agent for blueprint Q&A."""

from agents.blueprints.constants import ASK_AGENT
from agents.blueprints.sub_agents.ask.prompts import ASK_SYSTEM_PROMPT
from agents.blueprints.sub_agents.ask.tools import (
    get_common_blueprint_info,
    get_entity_info,
    get_field_info,
)
from agents.blueprints.sub_agents.react_agent_node import ReActAgentNode
from shared.config import Settings

ASK_TOOLS = [get_common_blueprint_info, get_entity_info, get_field_info]


class AskAgentNode(ReActAgentNode):
    """ReAct agent specialised for blueprint Q&A."""

    @classmethod
    def from_settings(cls, settings: Settings) -> "AskAgentNode":
        return super().from_settings(
            settings,
            system_prompt=ASK_SYSTEM_PROMPT,
            tools=ASK_TOOLS,
            agent_type=ASK_AGENT,
        )
