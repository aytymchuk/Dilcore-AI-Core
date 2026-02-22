"""LLM Stream Emitter — wraps astream calls to yield typed SSE events."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import PydanticOutputParser

from api.schemas.streaming import StreamEvent, StreamEventType
from shared.exceptions import TemplateParsingError
from shared.streaming.utils import is_thinking_chunk, parse_streaming_response

logger = logging.getLogger(__name__)


class StreamEmitter:
    """Coordinates LLM async streaming and emits typed StreamEvents.

    Converts raw LangChain chunks into a structured progression:
    THINKING → CONTENT → TEMPLATE → DONE (or ERROR).
    """

    def __init__(self, llm: BaseChatModel, messages: list[BaseMessage], parser: PydanticOutputParser) -> None:
        """Initialise the stream emitter.

        Args:
            llm: The underlying Language Model to call.
            messages: Pre-formatted chat history/prompts to send.
            parser: Used to parse the final accumulated output.
        """
        self._llm = llm
        self._messages = messages
        self._parser = parser

    async def stream(self) -> AsyncGenerator[StreamEvent, None]:
        """Stream template generation events from the LLM.

        Yields:
            StreamEvent objects representing chunks, completion, or errors.
        """
        accumulated_content = ""
        current_mode = StreamEventType.CONTENT

        try:
            from openai import APIConnectionError, APIError, RateLimitError

            async for chunk in self._llm.astream(self._messages):
                chunk_content = chunk.content if hasattr(chunk, "content") else ""
                if not chunk_content:
                    continue

                is_thinking = is_thinking_chunk(chunk)
                if is_thinking:
                    current_mode = StreamEventType.THINKING
                elif current_mode == StreamEventType.THINKING:
                    current_mode = StreamEventType.CONTENT

                accumulated_content += str(chunk_content)
                yield StreamEvent(event_type=current_mode, data=str(chunk_content))

            # Parse and yield final template
            template_response = parse_streaming_response(accumulated_content, self._parser)
            yield StreamEvent(
                event_type=StreamEventType.TEMPLATE,
                data=template_response.model_dump(mode="json"),
            )
            yield StreamEvent(event_type=StreamEventType.DONE, data="Stream completed")

        except (APIConnectionError, APIError, RateLimitError):
            logger.exception("LLM provider error during streaming")
            yield StreamEvent(event_type=StreamEventType.ERROR, data="Unable to communicate with AI provider")
        except (TemplateParsingError, Exception):
            logger.exception("Error during streaming generation")
            yield StreamEvent(event_type=StreamEventType.ERROR, data="Streaming generation failed")
