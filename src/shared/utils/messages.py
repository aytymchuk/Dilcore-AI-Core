"""LangChain message helpers."""

from __future__ import annotations

from langchain_core.messages import BaseMessage


def tag_ai_messages(messages: list[BaseMessage], agent_type: str) -> list[BaseMessage]:
    """Set ``metadata["agent_type"]`` on AI messages that don't already have one.

    Non-AI messages and AI messages that already carry an ``agent_type``
    are returned unchanged.

    .. deprecated::
        Prefer the ``create_agent_type_tagger`` middleware for ReAct agents.
    """
    tagged: list[BaseMessage] = []
    for msg in messages:
        kwargs = msg.additional_kwargs or {}
        if msg.type == "ai" and "agent_type" not in kwargs:
            new_kwargs = {**kwargs, "agent_type": agent_type}
            tagged.append(msg.model_copy(update={"additional_kwargs": new_kwargs}))
        else:
            tagged.append(msg)
    return tagged


def format_conversation(messages: list[BaseMessage]) -> str:
    """Flatten a message list into ``"type: content"`` lines.

    Empty-content messages are skipped.
    """
    return "\n".join(f"{m.type}: {m.content}" for m in messages if m.content)
