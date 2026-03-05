"""Handle response node — classifies user response as confirmation or corrections.

When the user accepted via a structured ``HumanResponse(type="accept")``,
``CollectUserResponseNode`` already sets ``generation_plan_confirmed = True``.
In that case this node is a no-op.  Otherwise it falls back to LLM
classification of the last human message.
"""

import logging

from langchain_core.messages import HumanMessage, SystemMessage

from agents.blueprints.models import ConfirmationClassification
from agents.blueprints.state import BlueprintsState
from agents.blueprints.sub_agents.generate.prompts import GENERATE_CONFIRMATION_CLASSIFIER_PROMPT
from infrastructure.llm import create_llm
from shared.config import Settings
from shared.models import LLMDecision

logger = logging.getLogger(__name__)


class HandleResponseNode:
    """Classifies the user's response as confirmation or corrections."""

    def __init__(self, settings: Settings):
        self._structured_llm = create_llm(settings).with_structured_output(LLMDecision[ConfirmationClassification])

    async def __call__(self, state: BlueprintsState) -> dict:
        if state.get("generation_plan_confirmed", False):
            logger.debug("Plan already confirmed by structured accept — skipping LLM classification.")
            return {}

        last_human_msg = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                last_human_msg = msg.content
                break

        try:
            output: LLMDecision[ConfirmationClassification] = await self._structured_llm.ainvoke(
                [
                    SystemMessage(content=GENERATE_CONFIRMATION_CLASSIFIER_PROMPT),
                    HumanMessage(content=last_human_msg),
                ]
            )
            confirmed = output.decision.decision == "confirmed"
            logger.debug("Confirmation classifier reasoning: %s", output.reasoning)
        except Exception:
            logger.exception("Failed to classify confirmation response. Defaulting to corrections.")
            confirmed = False

        return {"generation_plan_confirmed": confirmed}
