"""Write success node — skeleton placeholder for generation completion."""

from langchain_core.messages import AIMessage

from agents.blueprints.constants import GENERATE_AGENT
from agents.blueprints.state import BlueprintsState


class WriteSuccessNode:
    """Skeleton placeholder: reports that generation completed successfully."""

    async def __call__(self, state: BlueprintsState) -> dict:
        plan = state.get("generation_plan", [])
        count = len(plan)
        message = AIMessage(
            content=(
                f"Generation plan confirmed. All {count} action(s) have been "
                f"planned and simulated.\n\n"
                f"This is a skeleton response — actual execution will be implemented "
                f"in the next phase."
            ),
            additional_kwargs={"agent_type": GENERATE_AGENT},
        )
        return {"messages": [message]}
