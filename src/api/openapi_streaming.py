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
            "summary": "Sample sequence (thinking progress + reply chunks, terminal data)",
            "description": (
                "SSE stream: graph progress and streamed reasoning/assistant text as thinking steps "
                "with explicit status, then final `data` with messages and persisted reasoning envelopes."
            ),
            "value": (
                'data: {"category":"thinking","type":"reasoning","content":"Analyzing your request...","kind":"step","status":"completed","phase":"routing","after_message_id":"m-0","sequence":1,"node":"supervisor","agent_type":null}\n\n'
                'data: {"category":"thinking","type":"reasoning","content":"Classifying intent...","kind":"step","status":"running","after_message_id":"m-0","sequence":2,"node":"supervisor","agent_type":null}\n\n'
                'data: {"category":"thinking","type":"reasoning","content":"Hello","kind":"step","status":"running","after_message_id":"m-1","sequence":3,"node":"ask_agent","agent_type":"ask"}\n\n'
                'data: {"category":"data","thread_id":"00000000-0000-0000-0000-000000000000","messages":[{"id":"m-0","type":"human","content":"Hi","agent_type":null},{"id":"m-1","type":"ai","content":"Hello","agent_type":"ask"}],"reasoning":[{"id":"r-001","type":"reasoning","after_message_id":"m-0","sequence":1,"node":"supervisor","agent_type":null,"header":"Understanding what you want to do","steps":[{"kind":"step","status":"completed","content":"Analyzing your request...","items":null},{"kind":"step","status":"completed","content":"Classifying intent...","items":null}]},{"id":"r-002","type":"reasoning","after_message_id":"m-1","sequence":3,"node":"ask_agent","agent_type":"ask","header":null,"steps":[{"kind":"step","status":"completed","content":"Hello","items":null}]}]}\n\n'
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
