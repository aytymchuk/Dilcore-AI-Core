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
        interrupt_value = self._build_interrupt_value(state)
        response: Any = interrupt(interrupt_value)[0]

        resp_type = response.get("type", "response") if isinstance(response, dict) else "response"

        if resp_type == "accept":
            return {"generation_plan_confirmed": True}

        if resp_type == "edit":
            args = response.get("args", "") if isinstance(response, dict) else str(response)
            content = json.dumps(args) if not isinstance(args, str) else args
            return {"messages": [HumanMessage(content=content)]}

        # "response" (free-text) or any unrecognised type
        args = response.get("args", "") if isinstance(response, dict) else str(response)
        content = str(args) if args else ""
        return {"messages": [HumanMessage(content=content)]}
