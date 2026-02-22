"""Node to handle unclear user intent."""

from langchain_core.messages import AIMessage

from agents.blueprints.state import BlueprintsState


class IdentifyIntentNode:
    """Node to handle unclear user intent."""

    async def __call__(self, state: BlueprintsState) -> dict:
        """If user intent is not clear, ask for clarification."""
        message = AIMessage(
            content=(
                "Could you please clarify what you would like to do? "
                "Currently, I can help you understand blueprints or guide you through creating one."
            )
        )

        return {"messages": [message]}
