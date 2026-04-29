"""Write success node — skeleton placeholder for generation completion."""

from langchain_core.messages import AIMessage

from agents.blueprints.constants import GENERATE_AGENT
from agents.blueprints.state import BlueprintsState
from shared.reasoning import add_step, add_summary, set_header


class WriteSuccessNode:
    """Skeleton placeholder: reports that generation completed successfully."""

    async def __call__(self, state: BlueprintsState) -> dict:
        set_header("Wrapping up the approved plan")
        plan = state.get("generation_plan", [])
        count = len(plan)
        add_step(f"Marked {count} step(s) as ready for the next phase.", status="completed")
        add_summary(
            f"The approved plan with {count} step(s) is saved and ready for what comes next.",
            status="completed",
        )
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
