"""Node to handle unclear user intent."""

from langchain_core.messages import AIMessage

from agents.blueprints.state import BlueprintsState
from shared.reasoning import add_step, add_summary, set_header


class IdentifyIntentNode:
    """Node to handle unclear user intent."""

    async def __call__(self, state: BlueprintsState) -> dict:
        """If user intent is not clear, ask for clarification."""
        set_header("Making sure we understand you")
        add_step("I need a little more detail before continuing.", status="completed")
        add_summary(
            "I'll ask what you'd like to do next so we can point you to the right Blueprints help.",
            status="completed",
        )
        message = AIMessage(
            content=(
                "Could you please clarify what you would like to do? "
                "Currently, I can help you understand blueprints or guide you through creating one."
            )
        )

        return {"messages": [message]}
