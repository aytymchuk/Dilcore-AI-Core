"""Streaming AI agent implementation for SSE-based template generation."""

from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncGenerator
from typing import Any, Optional

from langchain_core.exceptions import OutputParserException
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser

from ai_agent.config import Settings
from ai_agent.exceptions import TemplateParsingError
from ai_agent.schemas.response import TemplateResponse
from ai_agent.schemas.streaming import (
    StreamEvent,
    StreamEventType,
    StreamingTemplateResponse,
)

from .base import StreamingAgent
from .prompts import STREAMING_GENERATION_PROMPT, STREAMING_SYSTEM_PROMPT
from .registry import AgentRegistry

logger = logging.getLogger(__name__)


@AgentRegistry.register("module-builder-streaming")
class StreamingModuleBuilderAgent(StreamingAgent):
    """AI Agent for streaming template generation with thinking mode support.

    This is the streaming version of ModuleBuilderAgent, useful for
    real-time feedback during template generation.
    """

    def __init__(self, settings: Settings) -> None:
        """Initialize the streaming agent with OpenRouter configuration.

        Args:
            settings: Application settings containing OpenRouter config.
        """
        super().__init__(settings)
        # Override LLM with streaming enabled
        from langchain_openai import ChatOpenAI

        self._llm = ChatOpenAI(
            api_key=settings.openrouter.api_key.get_secret_value(),
            base_url=settings.openrouter.base_url,
            model=settings.openrouter.model,
            temperature=0,  # Deterministic for structured output
            streaming=True,  # Enable streaming
        )
        self._parser = PydanticOutputParser(pydantic_object=TemplateResponse)

    @property
    def agent_type(self) -> str:
        """Return the agent type identifier."""
        return "module-builder"

    async def process(self, request: Any) -> StreamingTemplateResponse:
        """Process a generation request (non-streaming).

        Args:
            request: The request containing the prompt.

        Returns:
            StreamingTemplateResponse with template and explanation.
        """
        prompt = request.prompt if hasattr(request, "prompt") else str(request)

        # Collect all stream events and return final result
        final_response = None
        async for event in self.generate_template_stream(prompt):
            if event.event_type == StreamEventType.TEMPLATE:
                final_response = StreamingTemplateResponse(
                    template=TemplateResponse.model_validate(event.data),
                    explanation="Generated via streaming.",
                )

        if final_response is None:
            raise TemplateParsingError("Stream completed without generating a template")

        return final_response

    async def process_stream(self, request: Any) -> AsyncGenerator[StreamEvent, None]:
        """Process a request and stream the response.

        Args:
            request: The request containing the prompt.

        Yields:
            StreamEvent objects.
        """
        prompt = request.prompt if hasattr(request, "prompt") else str(request)
        async for event in self.generate_template_stream(prompt):
            yield event

    async def generate_template_stream(self, prompt: str) -> AsyncGenerator[StreamEvent, None]:
        """Stream template generation with thinking mode support.

        This method streams the AI generation process, supporting models with
        or without thinking mode. Events are yielded as they become available.

        Args:
            prompt: User's description of the template they want.

        Yields:
            StreamEvent objects with thinking, content, template, or done types.
        """
        logger.info("Starting streaming generation for prompt: %s", prompt[:100])

        # Build messages with streaming prompt
        messages = [
            SystemMessage(content=STREAMING_SYSTEM_PROMPT),
            HumanMessage(
                content=STREAMING_GENERATION_PROMPT.format(
                    prompt=prompt,
                    format_instructions=self._parser.get_format_instructions(),
                )
            ),
        ]

        accumulated_content = ""
        current_mode = StreamEventType.CONTENT  # Default to content mode

        try:
            from openai import APIConnectionError, APIError, RateLimitError

            async for chunk in self._llm.astream(messages):
                chunk_content = chunk.content if hasattr(chunk, "content") else ""

                if not chunk_content:
                    continue

                # Check for thinking mode in chunk metadata (model-specific)
                is_thinking = self._is_thinking_chunk(chunk)

                if is_thinking:
                    current_mode = StreamEventType.THINKING
                else:
                    # Once we exit thinking, stay in content mode
                    if current_mode == StreamEventType.THINKING and not is_thinking:
                        current_mode = StreamEventType.CONTENT

                # Accumulate for final parsing
                accumulated_content += chunk_content

                # Yield the chunk event
                yield StreamEvent(
                    event_type=current_mode,
                    data=chunk_content,
                )

            # Parse accumulated content into template + explanation
            template_response = self._parse_response(accumulated_content)

            # Yield final template event
            yield StreamEvent(
                event_type=StreamEventType.TEMPLATE,
                data=template_response.model_dump(mode="json"),
            )

            # Yield done event
            yield StreamEvent(
                event_type=StreamEventType.DONE,
                data="Stream completed",
            )

            logger.info(
                "Streaming generation completed for template: %s",
                template_response.template.template_id,
            )

        except (APIConnectionError, APIError, RateLimitError):
            logger.exception("LLM provider communication failed")
            error_msg = "Unable to communicate with AI provider"
            yield StreamEvent(
                event_type=StreamEventType.ERROR,
                data=error_msg,
            )

        except (OutputParserException, TemplateParsingError):
            logger.exception("Failed to parse LLM response")
            error_msg = "Unable to parse the generated template response"
            yield StreamEvent(
                event_type=StreamEventType.ERROR,
                data=error_msg,
            )

        except Exception:
            logger.exception("Unexpected error during streaming generation")
            error_msg = "An unexpected error occurred during template generation"
            yield StreamEvent(
                event_type=StreamEventType.ERROR,
                data=error_msg,
            )

    def _is_thinking_chunk(self, chunk) -> bool:
        """Detect if a chunk is part of thinking/reasoning output.

        This is model-specific. Some models include metadata indicating
        thinking mode, others may use special tokens or prefixes.

        Args:
            chunk: The LLM response chunk.

        Returns:
            True if this chunk is thinking content, False otherwise.
        """
        # Check for thinking indicator in response metadata
        if hasattr(chunk, "response_metadata"):
            metadata = chunk.response_metadata or {}
            if metadata.get("thinking") or metadata.get("reasoning"):
                return True

        # Check for additional_kwargs (some models use this)
        if hasattr(chunk, "additional_kwargs"):
            kwargs = chunk.additional_kwargs or {}
            if kwargs.get("thinking") or kwargs.get("is_thinking"):
                return True

        return False

    def _parse_response(self, content: str) -> StreamingTemplateResponse:
        """Parse accumulated response into template and explanation.

        Args:
            content: Full accumulated response content.

        Returns:
            StreamingTemplateResponse with parsed template and explanation.

        Raises:
            TemplateParsingError: If parsing fails.
        """
        try:
            # Extract JSON from markdown code block
            json_match = re.search(r"```json\s*([\s\S]*?)\s*```", content)

            if json_match:
                json_str = json_match.group(1).strip()
                template_data = json.loads(json_str)
                template = TemplateResponse.model_validate(template_data)
            else:
                # Try to parse the whole content as JSON (fallback)
                template = self._parser.parse(content)

            # Extract explanation
            explanation_match = re.search(r"EXPLANATION:\s*([\s\S]*?)(?:\Z|```)", content, re.IGNORECASE)
            explanation = (
                explanation_match.group(1).strip()
                if explanation_match
                else "Template generated based on the provided requirements."
            )

            return StreamingTemplateResponse(
                template=template,
                explanation=explanation,
            )

        except Exception as e:
            logger.exception("Failed to parse streaming response")
            raise TemplateParsingError("Unable to parse the generated template response") from e


# Backward compatibility aliases
StreamingTemplateAgent = StreamingModuleBuilderAgent


_streaming_agent_instance: Optional[StreamingModuleBuilderAgent] = None


def create_streaming_template_agent(settings: Settings) -> StreamingModuleBuilderAgent:
    """Create or return the singleton StreamingModuleBuilderAgent instance.

    Args:
        settings: Application settings.

    Returns:
        The StreamingModuleBuilderAgent instance.

    Note:
        This function is maintained for backward compatibility.
        Prefer using AgentRegistry.get_agent("module-builder-streaming", settings) instead.
    """
    global _streaming_agent_instance
    if _streaming_agent_instance is None:
        _streaming_agent_instance = StreamingModuleBuilderAgent(settings)
    return _streaming_agent_instance
