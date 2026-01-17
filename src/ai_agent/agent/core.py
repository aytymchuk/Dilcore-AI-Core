"""Core AI agent implementation using LangChain and OpenRouter."""

import logging
from typing import Optional

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from openai import APIConnectionError, APIError, RateLimitError

from ai_agent.config import Settings
from ai_agent.exceptions import (
    LLMProviderError,
    TemplateGenerationError,
    TemplateParsingError,
)
from ai_agent.schemas.response import TemplateResponse

from .prompts import SYSTEM_PROMPT, TEMPLATE_GENERATION_PROMPT

logger = logging.getLogger(__name__)


class TemplateAgent:
    """AI Agent for generating structured JSON templates."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the agent with OpenRouter configuration.

        Args:
            settings: Application settings containing OpenRouter config.
        """
        self._settings = settings
        self._llm = ChatOpenAI(
            api_key=settings.openrouter.api_key.get_secret_value(),
            base_url=settings.openrouter.base_url,
            model=settings.openrouter.model,
            temperature=0,  # Deterministic for structured output
        )
        self._parser = PydanticOutputParser(pydantic_object=TemplateResponse)

    async def generate_template(self, prompt: str) -> TemplateResponse:
        """Generate a template based on the user prompt.

        Args:
            prompt: User's description of the template they want.

        Returns:
            A structured TemplateResponse object.

        Raises:
            LLMProviderError: If communication with LLM provider fails.
            TemplateParsingError: If the LLM response cannot be parsed.
            TemplateGenerationError: For other generation failures.
        """
        logger.info("Generating template for prompt: %s", prompt[:100])

        # Build messages
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(
                content=TEMPLATE_GENERATION_PROMPT.format(prompt=prompt)
                + f"\n\n{self._parser.get_format_instructions()}"
            ),
        ]

        try:
            # Invoke LLM with structured output
            response = await self._llm.ainvoke(messages)

            # Parse response to TemplateResponse
            template = self._parser.parse(response.content)
            logger.info("Successfully generated template: %s", template.template_id)

            return template

        except (APIConnectionError, APIError, RateLimitError) as e:
            logger.exception("LLM provider communication failed")
            raise LLMProviderError("Unable to communicate with AI provider") from e

        except OutputParserException as e:
            logger.exception("Failed to parse LLM response")
            raise TemplateParsingError(
                "Unable to parse the generated template response"
            ) from e

        except Exception as e:
            logger.exception("Unexpected error during template generation")
            raise TemplateGenerationError(
                "An unexpected error occurred during template generation"
            ) from e


_agent_instance: Optional[TemplateAgent] = None


def create_template_agent(settings: Settings) -> TemplateAgent:
    """Create or return the singleton TemplateAgent instance.

    Args:
        settings: Application settings.

    Returns:
        The TemplateAgent instance.
    """
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = TemplateAgent(settings)
    return _agent_instance
