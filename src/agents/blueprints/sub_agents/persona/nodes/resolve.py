"""Resolve node — calls the LLM to pick the best form/view for the user request."""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from agents.blueprints.prompts import FORM_VIEW_RESOLUTION_PROMPT, PERSONA_SYSTEM_PROMPT
from api.schemas.persona import FormViewResolution, PersonaResponse

logger = logging.getLogger(__name__)


class ResolveIntentNode:
    """Use the LLM to resolve the user request to a form/view."""

    def __init__(self, llm: BaseChatModel | None) -> None:
        """Initialise node with the LLM dependency."""
        self._llm = llm

    async def __call__(self, state: dict[str, Any]) -> dict[str, Any]:
        """Execute intent resolution logic.

        Args:
            state: Persona graph state.

        Returns:
            Partial state update with ``persona_response``.
        """
        forms: list[dict] = state.get("relevant_forms", [])
        views: list[dict] = state.get("relevant_views", [])
        data: list[dict] = state.get("relevant_data", [])
        user_request: str = state["user_request"]

        metadata_items = [f"Form: {f.get('name', f.get('id', 'unknown'))}" for f in forms]
        metadata_items += [f"View: {v.get('name', v.get('id', 'unknown'))}" for v in views]
        metadata_context = "\n".join(metadata_items) if metadata_items else "No metadata available"

        messages = [
            SystemMessage(content=PERSONA_SYSTEM_PROMPT),
            HumanMessage(
                content=FORM_VIEW_RESOLUTION_PROMPT.format(
                    user_request=user_request,
                    metadata_context=metadata_context,
                )
            ),
        ]

        try:
            if self._llm is None:
                raise ValueError("LLM not configured in node")
            response = await self._llm.ainvoke(messages)
            best_match = forms[0] if forms else (views[0] if views else None)

            if best_match:
                resolution = FormViewResolution(
                    type="form" if forms else "view",
                    id=best_match.get("id", "unknown"),
                    name=best_match.get("name", "Unknown"),
                    operation="read",
                )
            else:
                resolution = FormViewResolution(
                    type="view",
                    id="default",
                    name="Default View",
                    operation="read",
                )

            persona_response = PersonaResponse(
                resolution=resolution,
                existing_data=data[0] if data else None,
                suggested_changes=[],
                explanation=response.content if hasattr(response, "content") else str(response),
            )
            return {"persona_response": persona_response, "error": None}

        except Exception as exc:
            logger.exception("ResolveIntentNode failed")
            fallback = PersonaResponse(
                resolution=FormViewResolution(type="view", id="error", name="Error", operation="read"),
                existing_data=None,
                suggested_changes=[],
                explanation=f"Could not process request: {exc}",
            )
            return {"persona_response": fallback, "error": str(exc)}
