"""Reusable OpenAPI fragments for Server-Sent Event (SSE) responses."""

from __future__ import annotations

from typing import Any

# Shared ``content["text/event-stream"]`` block for Blueprints stream endpoints.
BLUEPRINTS_SSE_STREAM_CONTENT: dict[str, Any] = {
    "schema": {
        "type": "string",
        "description": (
            "W3C Server-Sent Events (`text/event-stream`). "
            "Each event has a `data:` field whose value is a single JSON object "
            "matching the **BlueprintSseEvent** schema in `components.schemas` "
            "(discriminated union on `category`). Events are separated by a blank line (`\\n\\n`)."
        ),
    },
    "examples": {
        "mixed_turn": {
            "summary": "Sample sequence (status, delta, terminal data)",
            "description": (
                "Two SSE events: a routing status line, then the final `data` payload with an empty message list."
            ),
            "value": (
                'data: {"category":"status","message":"Analyzing your request...","phase":"routing"}\n\n'
                'data: {"category":"delta","content":"Hello","agent_type":"ask"}\n\n'
                'data: {"category":"data","thread_id":"00000000-0000-0000-0000-000000000000","messages":[]}\n\n'
            ),
        },
    },
}


def blueprints_sse_stream_success_response(
    *,
    status_code: int,
    description: str | None = None,
) -> dict[int | str, dict[str, Any]]:
    """OpenAPI ``responses`` entry for a successful SSE stream."""
    desc = description or (
        "Successful response opens an SSE stream. "
        "Parse each `data:` line as JSON; use `category` to distinguish event kinds."
    )
    return {
        status_code: {
            "description": desc,
            "content": {"text/event-stream": BLUEPRINTS_SSE_STREAM_CONTENT},
        }
    }
