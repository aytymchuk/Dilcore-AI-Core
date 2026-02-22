"""Generate node — produces the TemplateResponse from the LLM.

Takes the user prompt plus related entity context from the state, builds
the LangChain message list, calls the LLM, and parses the response.
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.exceptions import OutputParserException
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from openai import APIConnectionError, APIError, RateLimitError

from agents.blueprints.prompts import SYSTEM_PROMPT, TEMPLATE_GENERATION_PROMPT
from agents.blueprints.state import BlueprintsState
from api.schemas.response import TemplateResponse
from shared.exceptions import LLMProviderError, TemplateGenerationError, TemplateParsingError

logger = logging.getLogger(__name__)

_parser = PydanticOutputParser(pydantic_object=TemplateResponse)


class GenerateTemplateNode:
    """Call the LLM and parse a TemplateResponse from the output."""

    def __init__(self, llm: BaseChatModel | None) -> None:
        """Initialise the node with the LLM dependency.

        Args:
            llm: Chat model used for structured generation.
        """
        self._llm = llm

    async def __call__(self, state: BlueprintsState) -> dict[str, Any]:
        """Execute the template generation node logic.

        Args:
            state: Current graph state containing prompt and related logic.

        Returns:
            Partial state update with ``template_response`` or ``error``.
        """
        if self._llm is None:
            return {"error": "LLM client not configured"}

        prompt = state["prompt"]
        related = state.get("related_entities", [])
        context = state.get("context_entities", [])

        # Build context string
        context_str = ""
        all_entities = related + context
        if all_entities:
            entity_names = [e.get("name", e.get("id", "unknown")) for e in all_entities]
            context_str = f"\n\nExisting related entities: {', '.join(entity_names)}"

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=TEMPLATE_GENERATION_PROMPT.format(prompt=prompt)
                + context_str
                + f"\n\n{_parser.get_format_instructions()}"
            ),
        ]

        try:
            response = await self._llm.ainvoke(messages)
            template = _parser.parse(str(response.content))
            logger.info("Generated template: %s", template.template_id)
            return {"template_response": template, "error": None}

        except (APIConnectionError, APIError, RateLimitError) as exc:
            logger.exception("LLM provider error")
            raise LLMProviderError("Unable to communicate with AI provider") from exc

        except OutputParserException as exc:
            logger.exception("Failed to parse LLM response")
            raise TemplateParsingError("Unable to parse the generated template response") from exc

        except Exception as exc:
            logger.exception("Unexpected error during template generation")
            raise TemplateGenerationError("An unexpected error occurred during template generation") from exc
