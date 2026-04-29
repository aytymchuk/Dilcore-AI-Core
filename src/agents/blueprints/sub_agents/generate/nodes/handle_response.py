"""Handle response node — classifies user response as confirmation or corrections.

When the user accepted via a structured ``HumanResponse(type="accept")``,
``CollectUserResponseNode`` already sets ``generation_plan_confirmed = True``.
In that case this node is a no-op.  Otherwise it falls back to LLM
classification of the last human message.
"""

import logging
from collections.abc import Awaitable
from typing import cast

from langchain_core.messages import HumanMessage, SystemMessage

from agents.blueprints.models import ConfirmationClassification
from agents.blueprints.state import BlueprintsState
from agents.blueprints.sub_agents.generate.prompts import GENERATE_CONFIRMATION_CLASSIFIER_PROMPT
from infrastructure.llm import create_llm
from shared.config import Settings
from shared.models import LLMDecision
from shared.reasoning import add_step, add_summary, set_header, with_step

logger = logging.getLogger(__name__)


class HandleResponseNode:
    """Classifies the user's response as confirmation or corrections."""

    def __init__(self, settings: Settings):
        self._structured_llm = create_llm(settings).with_structured_output(LLMDecision[ConfirmationClassification])

    async def __call__(self, state: BlueprintsState) -> dict:
        set_header("Checking your plan feedback")
        if state.get("generation_plan_confirmed", False):
            logger.debug("Plan already confirmed by structured accept — skipping LLM classification.")
            add_step(
                "No extra check needed—you already approved the plan.",
                status="skipped",
            )
            add_summary("You're all set; the plan stays confirmed.", status="completed")
            return {}

        last_human_msg = ""
        for msg in reversed(state["messages"]):
            if isinstance(msg, HumanMessage):
                if isinstance(msg.content, list):
                    last_human_msg = " ".join(
                        part.get("text", "") if isinstance(part, dict) else str(part) for part in msg.content
                    )
                else:
                    last_human_msg = str(msg.content)
                break

        try:
            output: LLMDecision[ConfirmationClassification] = await with_step(
                "Reviewing whether you confirmed the plan or asked for changes",
                lambda: cast(
                    Awaitable[LLMDecision[ConfirmationClassification]],
                    self._structured_llm.ainvoke(
                        [
                            SystemMessage(content=GENERATE_CONFIRMATION_CLASSIFIER_PROMPT),
                            HumanMessage(content=last_human_msg),
                        ]
                    ),
                ),
            )
            confirmed = output.decision.decision == "confirmed"
            logger.debug("Confirmation classifier reasoning: %s", output.reasoning)
            verdict = "You confirmed the plan." if confirmed else "You asked for changes."
            add_summary(f"{verdict}\n\n{output.reasoning}".strip())
        except Exception:
            logger.exception("Failed to classify confirmation response. Defaulting to corrections.")
            confirmed = False
            add_step(
                "We couldn't read your reply clearly—assuming you'd like changes.",
                status="failed",
            )
            add_summary(
                "We'll treat your message as feedback so we can revise the plan.",
                status="completed",
            )

        return {"generation_plan_confirmed": confirmed}
