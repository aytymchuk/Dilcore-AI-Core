"""Shared utilities for LLM streaming and SSE."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from langchain_core.output_parsers import PydanticOutputParser

from api.schemas.response import TemplateResponse
from api.schemas.streaming import StreamEvent, StreamingTemplateResponse
from shared.exceptions import TemplateParsingError

logger = logging.getLogger(__name__)


def is_thinking_chunk(chunk: Any) -> bool:
    """Detect thinking/reasoning chunks (model-specific metadata).

    Checks payload for metadata indicating the provider is in a "thinking"
    phase rather than returning final content.
    """
    if hasattr(chunk, "response_metadata"):
        meta = chunk.response_metadata or {}
        if meta.get("thinking") or meta.get("reasoning"):
            return True
    if hasattr(chunk, "additional_kwargs"):
        kwargs = chunk.additional_kwargs or {}
        if kwargs.get("thinking") or kwargs.get("is_thinking"):
            return True
    return False


def parse_streaming_response(content: str, parser: PydanticOutputParser) -> StreamingTemplateResponse:
    """Parse accumulated streaming content into a StreamingTemplateResponse.

    Attempts to extract JSON from a markdown code block first, falling back
    to the provided Pydantic parser. Also extracts any conversational explanation.
    """
    try:
        json_match = re.search(r"```json\s*([\s\S]*?)\s*```", content)
        if json_match:
            template = TemplateResponse.model_validate(json.loads(json_match.group(1).strip()))
        else:
            template = parser.parse(content)

        explanation_match = re.search(r"EXPLANATION:\s*([\s\S]*?)(?:\Z|```)", content, re.IGNORECASE)
        explanation = (
            explanation_match.group(1).strip()
            if explanation_match
            else "Template generated based on the provided requirements."
        )
        return StreamingTemplateResponse(template=template, explanation=explanation)
    except Exception as exc:
        raise TemplateParsingError("Unable to parse the generated template response") from exc


def format_sse_event(event: StreamEvent) -> str:
    """Format a StreamEvent as a Server-Sent Events (SSE) string.

    SSE format requires:
    data: {"event_type": "...", "data": "..."}\n\n
    """
    return f"data: {event.model_dump_json()}\n\n"
