"""Streaming AI agent implementation for SSE-based template generation."""

from __future__ import annotations

import json
import logging
import re
from typing import AsyncGenerator, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI

from ai_agent.config import Settings
from ai_agent.schemas.response import TemplateResponse
from ai_agent.schemas.streaming import (
    StreamEvent,
    StreamEventType,
    StreamingTemplateResponse,
)

from .prompts import STREAMING_GENERATION_PROMPT, STREAMING_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class StreamingTemplateAgent:
    """AI Agent for streaming template generation with thinking mode support."""

    def __init__(self, settings: Settings) -> None:
        """Initialize the streaming agent with OpenRouter configuration.

        Args:
            settings: Application settings containing OpenRouter config.
        """
        self._settings = settings
        self._llm = ChatOpenAI(
            api_key=settings.openrouter.api_key.get_secret_value(),
            base_url=settings.openrouter.base_url,
            model=settings.openrouter.model,
            temperature=0,  # Deterministic for structured output
            streaming=True,  # Enable streaming
        )
        self._parser = PydanticOutputParser(pydantic_object=TemplateResponse)

    async def generate_template_stream(
        self, prompt: str
    ) -> AsyncGenerator[StreamEvent, None]:
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
            async for chunk in self._llm.astream(messages):
                chunk_content = chunk.content if hasattr(chunk, "content") else ""

                if not chunk_content:
                    continue

                # Check for thinking mode in chunk metadata (model-specific)
                # Different models may indicate thinking differently
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

        except Exception as e:
            logger.exception("Streaming generation failed")
            yield StreamEvent(
                event_type=StreamEventType.ERROR,
                data=str(e),
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
            ValueError: If parsing fails.
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
            explanation_match = re.search(
                r"EXPLANATION:\s*([\s\S]*?)(?:\Z|```)", content, re.IGNORECASE
            )
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
            raise ValueError(f"Failed to parse streaming response: {e}") from e


_streaming_agent_instance: Optional[StreamingTemplateAgent] = None


def create_streaming_template_agent(settings: Settings) -> StreamingTemplateAgent:
    """Create or return the singleton StreamingTemplateAgent instance.

    Args:
        settings: Application settings.

    Returns:
        The StreamingTemplateAgent instance.
    """
    global _streaming_agent_instance
    if _streaming_agent_instance is None:
        _streaming_agent_instance = StreamingTemplateAgent(settings)
    return _streaming_agent_instance
