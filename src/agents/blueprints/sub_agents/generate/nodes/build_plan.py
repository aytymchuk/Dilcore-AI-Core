"""Build plan node — analyzes conversation and design context to produce a generation plan.

Pre-loads API reference material (agent rules, entity/field API references) so
the planner LLM has full schema knowledge when producing the plan.
"""

import asyncio
import logging

from langchain_core.messages import HumanMessage, SystemMessage

from agents.blueprints.models import GenerationPlan, PlanAction
from agents.blueprints.state import BlueprintsState
from agents.blueprints.sub_agents.generate.prompts import GENERATE_PLANNER_PROMPT
from agents.blueprints.sub_agents.generate.tools import (
    get_agent_rules,
    get_entity_api_reference,
    get_field_api_reference,
)
from infrastructure.llm import create_llm
from shared.config import Settings
from shared.utils import format_conversation

logger = logging.getLogger(__name__)


class BuildPlanNode:
    """Analyzes conversation + design context and produces a generation plan."""

    _REFERENCE_TOOLS = [get_agent_rules, get_entity_api_reference, get_field_api_reference]

    def __init__(self, settings: Settings):
        self._structured_llm = create_llm(settings).with_structured_output(GenerationPlan)

    async def _load_reference_context(self) -> str:
        """Eagerly invoke all reference tools and concatenate their output."""

        async def _safe_invoke(t):
            try:
                return await t.ainvoke({})
            except Exception:
                logger.warning("Failed to load reference tool %s", t.name, exc_info=True)
                return None

        results = await asyncio.gather(*(_safe_invoke(t) for t in self._REFERENCE_TOOLS))
        sections = [r for r in results if r]
        return "\n\n---\n\n".join(sections)

    async def __call__(self, state: BlueprintsState) -> dict:
        design_context = state.get("design_context", "")

        reference = await self._load_reference_context()
        system_prompt = GENERATE_PLANNER_PROMPT
        if reference:
            system_prompt += f"\n\nAPI Reference Material:\n{reference}"

        conversation = format_conversation(state["messages"])
        human_content = conversation
        if design_context:
            human_content = f"Design context:\n{design_context}\n\n---\n\n{conversation}"

        try:
            plan: GenerationPlan = await self._structured_llm.ainvoke(
                [
                    SystemMessage(content=system_prompt),
                    HumanMessage(content=human_content),
                ]
            )
            actions = plan.actions
        except Exception:
            logger.exception("Failed to parse generation plan via structured output.")
            actions = [
                PlanAction(action="raw_plan", target="all", description="Plan generation failed — please retry.")
            ]

        return {
            "generation_plan": actions,
            "generation_plan_confirmed": False,
        }
