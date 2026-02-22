"""In-memory checkpointer for LangGraph."""

from langgraph.checkpoint.memory import MemorySaver

# Singleton checkpointer for the application lifecycle
_memory_saver = MemorySaver()


def get_checkpointer() -> MemorySaver:
    """Return the singleton MemorySaver instance."""
    return _memory_saver
