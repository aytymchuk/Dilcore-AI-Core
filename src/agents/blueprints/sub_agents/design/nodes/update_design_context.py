"""Update design context node — summarizes conversation into structured design decisions."""

from langchain_core.messages import AIMessage, SystemMessage

from agents.blueprints.state import BlueprintsState
from agents.blueprints.sub_agents.design.prompts import DESIGN_CONTEXT_SUMMARIZER_PROMPT
from infrastructure.llm import create_llm
from shared.config import Settings
from shared.utils import format_conversation


class UpdateDesignContextNode:
    """Summarizes the conversation into a structured design context."""

    def __init__(self, settings: Settings):
        self._llm = create_llm(settings)

    async def __call__(self, state: BlueprintsState) -> dict:
        existing_context = state.get("design_context", "")
        prompt = DESIGN_CONTEXT_SUMMARIZER_PROMPT.format(
            existing_context=existing_context or "(none)",
        )

        conversation = format_conversation(state["messages"])

        response = await self._llm.ainvoke(
            [
                SystemMessage(content=prompt),
                AIMessage(content=conversation),
            ]
        )

        return {"design_context": response.content}
