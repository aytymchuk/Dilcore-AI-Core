"""Present plan node — formats the generation plan for user review."""

from langchain_core.messages import AIMessage

from agents.blueprints.constants import GENERATE_AGENT
from agents.blueprints.state import BlueprintsState


class PresentPlanNode:
    """Formats the plan as a human-readable message for user review."""

    async def __call__(self, state: BlueprintsState) -> dict:
        plan = state.get("generation_plan", [])

        lines = ["Here is the generation plan. Please review and confirm, or provide corrections:\n"]
        for i, task in enumerate(plan, 1):
            action = getattr(task, "action", "unknown")
            target = getattr(task, "target", "")
            description = getattr(task, "description", "")
            lines.append(f"{i}. **{action}** — {target}: {description}")

        lines.append("\nReply with **confirm** to proceed, or describe any changes you'd like.")

        return {"messages": [AIMessage(content="\n".join(lines), additional_kwargs={"agent_type": GENERATE_AGENT})]}
