"""Collect user response node — HITL interrupt that waits for user confirmation.

Uses the ``HumanInterrupt`` / ``HumanResponse`` pattern so the client
receives a structured interrupt payload and can respond with
accept / respond / edit.
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.types import interrupt

from agents.blueprints.models import (
    ActionRequest,
    HumanInterrupt,
    HumanInterruptConfig,
)
from agents.blueprints.state import BlueprintsState
from shared.reasoning import add_step, add_summary, set_header


class CollectUserResponseNode:
    """Pauses the graph and waits for the user to confirm or correct the plan.

    Emits a structured ``HumanInterrupt`` via ``interrupt()``.  The caller
    resumes with ``Command(resume=<HumanResponse>)``.  The node interprets
    the response type and updates state accordingly:

    - ``accept``  -> sets ``generation_plan_confirmed = True`` directly.
    - ``response`` -> stores the free-text feedback as a ``HumanMessage``.
    - ``edit``    -> serialises the edited ``ActionRequest`` as a ``HumanMessage``.
    """

    def _build_interrupt_value(self, state: BlueprintsState) -> list[HumanInterrupt]:
        plan = state.get("generation_plan", [])
        plan_dicts = [p.model_dump() if hasattr(p, "model_dump") else dict(p) for p in plan]

        return [
            HumanInterrupt(
                action_request=ActionRequest(
                    action="confirm_plan",
                    args={"plan": plan_dicts},
                ),
                config=HumanInterruptConfig(
                    allow_ignore=False,
                    allow_respond=True,
                    allow_edit=True,
                    allow_accept=True,
                ),
                description="Review and confirm the generation plan.",
            )
        ]

    async def __call__(self, state: BlueprintsState) -> dict:
        set_header("Waiting for your review")
        add_step("Pausing until you approve the plan or send feedback.", status="running")
        interrupt_value = self._build_interrupt_value(state)
        response: Any = interrupt(interrupt_value)[0]

        resp_type = response.get("type", "response") if isinstance(response, dict) else "response"

        if resp_type == "accept":
            add_step("You approved the plan as shown.", status="completed")
            add_step("No edits were sent this time.", status="skipped")
            add_step("No written corrections were sent this time.", status="skipped")
            add_summary("You confirmed the plan—we can move forward.", status="completed")
            return {"generation_plan_confirmed": True}

        if resp_type == "edit":
            add_step("You changed items in the plan.", status="completed")
            add_step("You didn't approve the plan exactly as shown.", status="skipped")
            add_step("You didn't send free-text corrections.", status="skipped")
            add_summary("We'll take your edits and refresh the plan.", status="completed")
            args = response.get("args", "") if isinstance(response, dict) else str(response)
            content = json.dumps(args) if not isinstance(args, str) else args
            return {"messages": [HumanMessage(content=content)]}

        # "response" (free-text) or any unrecognised type
        add_step("You asked for changes in your own words.", status="completed")
        add_step("You didn't approve the plan exactly as shown.", status="skipped")
        add_step("You didn't use the structured edit option.", status="skipped")
        add_summary("We'll use your feedback to revise the plan.", status="completed")
        args = response.get("args", "") if isinstance(response, dict) else str(response)
        content = str(args) if args else ""
        return {"messages": [HumanMessage(content=content)]}
