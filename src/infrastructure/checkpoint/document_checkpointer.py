"""MongoDB-based checkpointer for LangGraph."""

from __future__ import annotations

from functools import lru_cache

from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pymongo import MongoClient

from shared.config import get_settings

_mongo_client: MongoClient | None = None


@lru_cache
def get_checkpointer() -> MongoDBSaver:
    """Return a singleton MongoDBSaver instance for checkpoint persistence."""
    global _mongo_client  # noqa: PLW0603
    settings = get_settings()
    _mongo_client = MongoClient(settings.mongodb.connection_string)

    # Explicitly allow agents.blueprints.models for msgpack deserialization
    # to silence warnings for custom types (e.g., PlanAction).
    serde = JsonPlusSerializer(allowed_msgpack_modules=("agents.blueprints.models",))

    return MongoDBSaver(_mongo_client, db_name=settings.mongodb.db_name, serde=serde)


def close_checkpointer() -> None:
    """Close the underlying MongoClient and invalidate the cached saver."""
    global _mongo_client  # noqa: PLW0603
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
    get_checkpointer.cache_clear()
