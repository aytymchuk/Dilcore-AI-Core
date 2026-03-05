"""Design agent node — runs the inner ReAct agent for collaborative planning."""

from agents.blueprints.constants import DESIGN_AGENT
from agents.blueprints.sub_agents.ask.tools import (
    get_common_blueprint_info,
    get_entity_info,
    get_field_info,
)
from agents.blueprints.sub_agents.design.prompts import DESIGN_SYSTEM_PROMPT
from agents.blueprints.sub_agents.react_agent_node import ReActAgentNode
from shared.config import Settings

DESIGN_TOOLS = [get_common_blueprint_info, get_entity_info, get_field_info]


class DesignAgentNode(ReActAgentNode):
    """ReAct agent specialised for collaborative blueprint design."""

    @classmethod
    def from_settings(cls, settings: Settings) -> "DesignAgentNode":
        return super().from_settings(
            settings,
            system_prompt=DESIGN_SYSTEM_PROMPT,
            tools=DESIGN_TOOLS,
            agent_type=DESIGN_AGENT,
        )
