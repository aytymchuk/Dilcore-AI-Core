"""Update design context node — summarizes conversation into structured design decisions."""

from collections.abc import Awaitable
from typing import cast

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agents.blueprints.state import BlueprintsState
from agents.blueprints.sub_agents.design.prompts import DESIGN_CONTEXT_SUMMARIZER_PROMPT
from infrastructure.llm import create_llm
from shared.config import Settings
from shared.reasoning import add_next_steps, add_summary, set_header, with_step
from shared.utils import format_conversation


class UpdateDesignContextNode:
    """Summarizes the conversation into a structured design context."""

    def __init__(self, settings: Settings):
        self._llm = create_llm(settings)

    async def __call__(self, state: BlueprintsState) -> dict:
        set_header("Updating what we know about your blueprint")
        existing_context = state.get("design_context", "")
        prompt = DESIGN_CONTEXT_SUMMARIZER_PROMPT.replace(
            "{existing_context}",
            existing_context or "(none)",
        )

        conversation = format_conversation(state["messages"])

        response = await with_step(
            "Reviewing the conversation so far",
            lambda: cast(
                Awaitable[AIMessage],
                self._llm.ainvoke(
                    [
                        SystemMessage(content=prompt),
                        HumanMessage(content=conversation),
                    ]
                ),
            ),
        )

        add_summary(
            "Your blueprint notes are updated so we can keep designing or move on to planning.",
            status="completed",
        )
        add_next_steps(
            ["If you ask for generation next, we'll use these notes in the plan."],
            status="completed",
        )
        return {"design_context": response.content}
