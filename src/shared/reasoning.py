"""Reasoning / thinking utilities shared across streaming and persistence.

This module intentionally deals only with provider-exposed reasoning blocks
(LangChain-normalized content blocks such as type="reasoning"/"thinking") and
explicit structured rationale produced by our own prompts (e.g. LLMDecision.reasoning).

It must not attempt to reconstruct hidden chain-of-thought.

Design goals:
- Thread-safe per conversation/run (contextvar-backed buffer).
- Fluent API for nodes: add_step/add_summary/add_next_steps.
- Reasoning envelopes are *anchored* to message ids so they can be rendered after
  the correct message during replay.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Awaitable, Callable, Iterable, Sequence
from contextvars import ContextVar
from dataclasses import dataclass, field, replace
from inspect import isawaitable
from typing import Any, Literal, cast, overload

ReasoningType = Literal["thinking", "reasoning"]
ReasoningKind = Literal["step", "summary", "next_steps"]
ReasoningStatus = Literal["running", "completed", "failed", "skipped"]


@dataclass(frozen=True, slots=True)
class ReasoningEntry:
    kind: ReasoningKind
    status: ReasoningStatus = "running"
    content: str | None = None
    items: list[str] | None = None


@dataclass(frozen=True, slots=True)
class ReasoningEnvelope:
    """A contiguous reasoning envelope anchored after a message."""

    id: str
    type: ReasoningType
    after_message_id: str
    sequence: int
    node: str | None = None
    agent_type: str | None = None
    header: str | None = None
    steps: tuple[ReasoningEntry, ...] = ()


def _coerce_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def extract_reasoning_delta(obj: Any) -> tuple[ReasoningType, str] | None:
    """Extract a reasoning/thinking delta from a streamed message chunk or message.

    Supports:
    - LangChain normalized content blocks in ``content`` list with block types:
      - "reasoning" (preferred)
      - "thinking" (legacy/provider-specific)
    - Provider fallbacks:
      - ``reasoning_content`` attribute
      - ``additional_kwargs["reasoning_content"]``

    Returns (type, delta_text) or None.
    """

    rc = getattr(obj, "reasoning_content", None)
    if rc:
        s = _coerce_str(rc)
        return ("reasoning", s) if s else None

    additional = getattr(obj, "additional_kwargs", None) or {}
    nested = additional.get("reasoning_content")
    if nested:
        s = _coerce_str(nested)
        return ("reasoning", s) if s else None

    content = getattr(obj, "content", None)
    if isinstance(content, list):
        parts: list[str] = []
        seen_type: ReasoningType | None = None
        for block in content:
            if not isinstance(block, dict):
                continue
            block_type = block.get("type")
            if block_type not in ("thinking", "reasoning"):
                continue
            if seen_type is None:
                seen_type = "reasoning" if block_type == "reasoning" else "thinking"
            piece = block.get("thinking") or block.get("reasoning") or block.get("text")
            if piece:
                parts.append(str(piece))
        if parts and seen_type is not None:
            return (seen_type, "".join(parts))

    return None


def extract_text_delta(obj: Any) -> str | None:
    """Extract visible assistant text delta from a streamed message chunk or message."""

    content = getattr(obj, "content", None)
    if content is None:
        return None
    if isinstance(content, str) and content:
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, str):
                parts.append(block)
            elif isinstance(block, dict) and block.get("type") == "text":
                parts.append(str(block.get("text", "")))
        joined = "".join(parts)
        return joined if joined else None
    return None


def extract_agent_type(obj: Any) -> str | None:
    additional = getattr(obj, "additional_kwargs", None) or {}
    at = additional.get("agent_type")
    return str(at) if at is not None else None


@dataclass(slots=True)
class ReasoningBuffer:
    """Per-run collector for anchored reasoning envelopes."""

    thread_id: str
    anchor_message_id: str
    sequence_base: int = 0
    _next_sequence: int = field(init=False, default=0)
    _envelopes: list[ReasoningEnvelope] = field(default_factory=list)
    _open: ReasoningEnvelope | None = None
    _closed_by_text: bool = field(init=False, default=False)

    def __post_init__(self) -> None:
        self._next_sequence = self.sequence_base

    def _alloc_sequence(self) -> int:
        self._next_sequence += 1
        return self._next_sequence

    def close_on_text_delta(self, *, new_anchor_message_id: str) -> None:
        """Close current envelope boundary after assistant text appears."""
        # Mark any running steps in the currently open envelope as completed.
        if self._open is not None and self._open.steps:
            steps: list[ReasoningEntry] = []
            changed = False
            for s in self._open.steps:
                if s.status == "running":
                    steps.append(ReasoningEntry(kind=s.kind, status="completed", content=s.content, items=s.items))
                    changed = True
                else:
                    steps.append(s)
            if changed:
                new_env = replace(self._open, steps=tuple(steps))
                self._envelopes[-1] = new_env
                self._open = new_env
        self._open = None
        self._closed_by_text = True
        self.anchor_message_id = new_anchor_message_id

    def _ensure_envelope(
        self,
        *,
        r_type: ReasoningType,
        node: str | None,
        agent_type: str | None,
    ) -> ReasoningEnvelope:
        allow_concat = not self._closed_by_text
        if (
            allow_concat
            and self._open is not None
            and self._open.type == r_type
            and self._open.after_message_id == self.anchor_message_id
            and self._open.node == node
            and self._open.agent_type == agent_type
        ):
            return self._open

        env = ReasoningEnvelope(
            id=f"r-{uuid.uuid4()}",
            type=r_type,
            after_message_id=self.anchor_message_id,
            sequence=self._alloc_sequence(),
            node=node,
            agent_type=agent_type,
            header=None,
            steps=(),
        )
        self._envelopes.append(env)
        self._open = env
        self._closed_by_text = False
        return env

    def _append_entry(self, env: ReasoningEnvelope, entry: ReasoningEntry) -> ReasoningEnvelope:
        # Concatenate if same kind and both are text-like (provider emits many deltas)
        if env.steps:
            last = env.steps[-1]
            if (
                last.kind == entry.kind
                and last.status == entry.status
                and last.content is not None
                and entry.content is not None
                and last.items is None
            ):
                merged_last = ReasoningEntry(kind=last.kind, status=last.status, content=last.content + entry.content)
                new_steps = env.steps[:-1] + (merged_last,)
                new_env = replace(env, steps=new_steps)
                self._envelopes[-1] = new_env
                self._open = new_env
                return new_env
        new_steps = env.steps + (entry,)
        new_env = replace(env, steps=new_steps)
        self._envelopes[-1] = new_env
        self._open = new_env
        return new_env

    def add_step(
        self,
        content: str,
        *,
        status: ReasoningStatus = "completed",
        node: str | None = None,
        agent_type: str | None = None,
    ) -> ReasoningEnvelope:
        env = self._ensure_envelope(r_type="reasoning", node=node, agent_type=agent_type)
        return self._append_entry(env, ReasoningEntry(kind="step", status=status, content=content))

    def add_summary(
        self,
        content: str,
        *,
        status: ReasoningStatus = "completed",
        node: str | None = None,
        agent_type: str | None = None,
    ) -> ReasoningEnvelope:
        env = self._ensure_envelope(r_type="reasoning", node=node, agent_type=agent_type)
        return self._append_entry(env, ReasoningEntry(kind="summary", status=status, content=content))

    def add_next_steps(
        self,
        items: Sequence[str],
        *,
        status: ReasoningStatus = "completed",
        node: str | None = None,
        agent_type: str | None = None,
    ) -> ReasoningEnvelope:
        env = self._ensure_envelope(r_type="reasoning", node=node, agent_type=agent_type)
        return self._append_entry(env, ReasoningEntry(kind="next_steps", status=status, items=list(items)))

    def add_provider_delta(
        self,
        r_type: ReasoningType,
        content: str,
        *,
        status: ReasoningStatus = "running",
        node: str | None = None,
        agent_type: str | None = None,
    ) -> ReasoningEnvelope:
        env = self._ensure_envelope(r_type=r_type, node=node, agent_type=agent_type)
        return self._append_entry(env, ReasoningEntry(kind="step", status=status, content=content))

    def add_assistant_reply_delta(
        self,
        content: str,
        *,
        node: str | None = None,
        agent_type: str | None = None,
    ) -> ReasoningEnvelope:
        """Append streamed visible assistant answer text as reasoning steps.

        Chunks merge into one running step (same as :meth:`add_provider_delta` with
        ``r_type="reasoning"``) so replay shows process/context plus the assistant reply.
        Call :meth:`finalize_streaming_steps` before persisting so steps are finalized.
        """
        return self.add_provider_delta(
            "reasoning",
            content,
            status="running",
            node=node,
            agent_type=agent_type,
        )

    def finalize_streaming_steps(self, *, success: bool = True) -> None:
        """Mark any running reasoning entries before persistence or stream failure.

        Successful streams finalize ``running`` steps as ``completed``. When ``success`` is
        false (e.g. stream-level error), ``running`` steps become ``failed``.
        """
        terminal: ReasoningStatus = "completed" if success else "failed"
        for env_i, env in enumerate(self._envelopes):
            changed = False
            steps: list[ReasoningEntry] = []
            for s in env.steps:
                if s.status == "running":
                    steps.append(ReasoningEntry(kind=s.kind, status=terminal, content=s.content, items=s.items))
                    changed = True
                else:
                    steps.append(s)
            if changed:
                new_env = replace(env, steps=tuple(steps))
                self._envelopes[env_i] = new_env
                if self._open is not None and self._open.id == env.id:
                    self._open = new_env

    def update_entry_status(
        self,
        *,
        envelope_id: str,
        entry_index: int,
        status: ReasoningStatus,
    ) -> ReasoningEnvelope | None:
        for env_i, env in enumerate(self._envelopes):
            if env.id != envelope_id or not 0 <= entry_index < len(env.steps):
                continue

            steps = list(env.steps)
            entry = steps[entry_index]
            steps[entry_index] = ReasoningEntry(
                kind=entry.kind,
                status=status,
                content=entry.content,
                items=entry.items,
            )
            new_env = replace(env, steps=tuple(steps))
            self._envelopes[env_i] = new_env
            if self._open is not None and self._open.id == envelope_id:
                self._open = new_env
            return new_env
        return None

    def envelopes(self) -> list[ReasoningEnvelope]:
        return list(self._envelopes)

    def set_header(
        self,
        content: str,
        *,
        r_type: ReasoningType = "reasoning",
        node: str | None = None,
        agent_type: str | None = None,
    ) -> ReasoningEnvelope:
        env = self._ensure_envelope(r_type=r_type, node=node, agent_type=agent_type)
        new_env = replace(env, header=content)
        self._envelopes[-1] = new_env
        self._open = new_env
        return new_env


def serialize_reasoning_envelopes(envelopes: Iterable[ReasoningEnvelope]) -> list[dict[str, Any]]:
    return [
        {
            "id": e.id,
            "type": e.type,
            "after_message_id": e.after_message_id,
            "sequence": e.sequence,
            "node": e.node,
            "agent_type": e.agent_type,
            "header": e.header,
            "steps": [{"kind": s.kind, "status": s.status, "content": s.content, "items": s.items} for s in e.steps],
        }
        for e in envelopes
    ]


def deserialize_reasoning_envelopes(raw: Any) -> list[ReasoningEnvelope]:
    if not raw:
        return []
    if not isinstance(raw, list):
        return []
    out: list[ReasoningEnvelope] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        t = item.get("type")
        if t not in ("thinking", "reasoning"):
            continue
        after_message_id = item.get("after_message_id")
        if not isinstance(after_message_id, str) or not after_message_id:
            continue
        seq = item.get("sequence")
        if not isinstance(seq, int):
            continue
        steps_raw = item.get("steps") or []
        steps: list[ReasoningEntry] = []
        if isinstance(steps_raw, list):
            for s in steps_raw:
                if not isinstance(s, dict):
                    continue
                kind = s.get("kind")
                if kind not in ("step", "summary", "next_steps"):
                    continue
                status = s.get("status")
                if status not in ("running", "completed", "failed", "skipped"):
                    status = "completed"
                if kind == "next_steps":
                    items = s.get("items")
                    if isinstance(items, list):
                        steps.append(ReasoningEntry(kind="next_steps", status=status, items=[str(x) for x in items]))
                else:
                    c = s.get("content")
                    if isinstance(c, str) and c:
                        steps.append(ReasoningEntry(kind=kind, status=status, content=c))

        out.append(
            ReasoningEnvelope(
                id=_coerce_str(item.get("id")) or f"r-{uuid.uuid4()}",
                type=t,
                after_message_id=after_message_id,
                sequence=seq,
                node=_coerce_str(item.get("node")),
                agent_type=_coerce_str(item.get("agent_type")),
                header=_coerce_str(item.get("header")),
                steps=tuple(steps),
            )
        )
    return out


_BUFFER: ContextVar[ReasoningBuffer | None] = ContextVar("reasoning_buffer", default=None)
_CURRENT_NODE: ContextVar[str | None] = ContextVar("reasoning_node", default=None)


def set_reasoning_buffer(buffer: ReasoningBuffer) -> Any:
    """Set buffer for the current async context; returns token for reset()."""
    return _BUFFER.set(buffer)


def reset_reasoning_buffer(token: Any) -> None:
    _BUFFER.reset(token)


def _get_reasoning() -> ReasoningBuffer:
    """Get the current reasoning buffer (must exist inside an agent run)."""
    buf = _BUFFER.get()
    if buf is None:
        raise RuntimeError("No active ReasoningBuffer in this context")
    return buf


def _try_get_reasoning() -> ReasoningBuffer | None:
    return _BUFFER.get()


def add_step(
    content: str,
    *,
    status: ReasoningStatus = "completed",
    agent_type: str | None = None,
) -> ReasoningEnvelope | None:
    buf = _try_get_reasoning()
    if buf is None:
        return None
    return buf.add_step(content, status=status, node=_CURRENT_NODE.get(), agent_type=agent_type)


def add_summary(
    content: str,
    *,
    status: ReasoningStatus = "completed",
    agent_type: str | None = None,
) -> ReasoningEnvelope | None:
    buf = _try_get_reasoning()
    if buf is None:
        return None
    return buf.add_summary(content, status=status, node=_CURRENT_NODE.get(), agent_type=agent_type)


def add_next_steps(
    items: Sequence[str],
    *,
    status: ReasoningStatus = "completed",
    agent_type: str | None = None,
) -> ReasoningEnvelope | None:
    buf = _try_get_reasoning()
    if buf is None:
        return None
    return buf.add_next_steps(items, status=status, node=_CURRENT_NODE.get(), agent_type=agent_type)


def set_header(content: str, *, agent_type: str | None = None) -> ReasoningEnvelope | None:
    buf = _try_get_reasoning()
    if buf is None:
        return None
    return buf.set_header(content, node=_CURRENT_NODE.get(), agent_type=agent_type)


@overload
async def with_step[T](
    content: str,
    call: Callable[[], Awaitable[T]],
    *,
    agent_type: str | None = None,
) -> T: ...


@overload
async def with_step[T](
    content: str,
    call: Callable[[], T],
    *,
    agent_type: str | None = None,
) -> T: ...


async def with_step[T](
    content: str,
    call: Callable[[], Awaitable[T] | T],
    *,
    agent_type: str | None = None,
) -> T:
    """Run ``call`` while updating one reasoning step from running to completed/failed."""
    buf = _try_get_reasoning()
    env = None
    entry_index = -1
    if buf is not None:
        env = buf.add_step(content, status="running", node=_CURRENT_NODE.get(), agent_type=agent_type)
        entry_index = len(env.steps) - 1

    try:
        result = call()
        if isawaitable(result):
            result = await result
    except Exception:
        if buf is not None and env is not None:
            buf.update_entry_status(envelope_id=env.id, entry_index=entry_index, status="failed")
        raise

    if buf is not None and env is not None:
        buf.update_entry_status(envelope_id=env.id, entry_index=entry_index, status="completed")
    return cast(T, result)


def with_reasoning_node(node_name: str, node: Any) -> Any:
    """Wrap a graph node so reasoning entries are attributed without node-level boilerplate."""

    async def _wrapped(*args: Any, **kwargs: Any) -> Any:
        token = _CURRENT_NODE.set(node_name)
        try:
            result = node(*args, **kwargs)
            if isawaitable(result):
                return await result
            return result
        finally:
            _CURRENT_NODE.reset(token)

    return _wrapped


@dataclass(slots=True)
class SupervisorStructuredCaptureState:
    """Tracks streamed AIMessage text that is actually JSON for ``LLMDecision``."""

    buf: str = ""
    capturing: bool = False


def _extract_balanced_json_prefix(raw: str) -> tuple[str, str] | None:
    """If ``raw`` begins (after optional whitespace) with ``{``, return ``(json_str, rest)`` when braces balance."""
    i = 0
    n = len(raw)
    while i < n and raw[i].isspace():
        i += 1
    if i >= n or raw[i] != "{":
        return None
    start = i
    depth = 0
    in_string = False
    escape = False
    while i < n:
        c = raw[i]
        if escape:
            escape = False
        elif c == "\\" and in_string:
            escape = True
        elif c == '"' and not escape:
            in_string = not in_string
        elif not in_string:
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return raw[start : i + 1], raw[i + 1 :]
        i += 1
    return None


def _try_parse_llm_decision_json(prefix: str) -> dict[str, Any] | None:
    try:
        data = json.loads(prefix)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    dec = data.get("decision")
    if not isinstance(dec, dict) or "next_route" not in dec:
        return None
    if "reasoning" not in data:
        return None
    return data


def consume_supervisor_structured_delta(
    state: SupervisorStructuredCaptureState,
    text: str,
    *,
    agent_type: str | None,
) -> tuple[str | None, list[dict[str, Any]]]:
    """Split streamed assistant text into client-visible deltas vs supervisor JSON.

    Structured routing uses ``with_structured_output(LLMDecision)``, which often streams
    raw JSON as AIMessage text before subgraph tools run. Those chunks should not be shown
    as visible assistant reply chunks (reasoning steps).

    Returns ``(text_to_append_as_visible_reply_or_None, side_effects)``. Side effect kinds:
    - ``supervisor_stream_start``: first suppressed chunk for this JSON stream.
    - ``supervisor_stream_parsed``: JSON completed; includes ``reasoning`` and ``next_route`` strings.

    Sub-agent replies set ``agent_type`` on chunks; we never capture those as routing JSON.
    """
    effects: list[dict[str, Any]] = []

    def flush_buffer_as_plain(tail: str) -> tuple[str | None, list[dict[str, Any]]]:
        merged = state.buf + tail
        state.buf = ""
        state.capturing = False
        return (merged if merged else None), []

    if agent_type is not None:
        return flush_buffer_as_plain(text)

    if not text:
        return None, []

    if not state.capturing:
        lead = text.lstrip()
        if not lead.startswith("{"):
            return text, []

        state.capturing = True
        state.buf = text
        effects.append({"kind": "supervisor_stream_start"})
    else:
        state.buf += text

    parsed_prefix = _extract_balanced_json_prefix(state.buf)
    if parsed_prefix is None:
        return None, effects

    json_str, rest = parsed_prefix
    data = _try_parse_llm_decision_json(json_str)
    if data is None:
        plain = state.buf
        state.buf = ""
        state.capturing = False
        tail_text, tail_effects = consume_supervisor_structured_delta(state, rest, agent_type=None)
        merged = plain + (tail_text or "")
        return (merged if merged else None), tail_effects

    reasoning = data.get("reasoning")
    route = data["decision"]["next_route"]
    nr = str(route) if route is not None else ""
    reasoning_s = reasoning if isinstance(reasoning, str) else ""

    state.buf = ""
    state.capturing = False
    effects.append(
        {
            "kind": "supervisor_stream_parsed",
            "reasoning": reasoning_s,
            "next_route": nr,
        }
    )

    if not rest.strip():
        return None, effects

    tail_text, tail_effects = consume_supervisor_structured_delta(state, rest, agent_type=None)
    return tail_text, effects + tail_effects
