"""MongoDB-based checkpointer for LangGraph."""

from functools import lru_cache

from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient

from shared.config import get_settings


@lru_cache
def get_checkpointer() -> MongoDBSaver:
    """Return a singleton MongoDBSaver instance for checkpoint persistence."""
    settings = get_settings()
    client = MongoClient(settings.mongodb.connection_string)
    return MongoDBSaver(client, db_name=settings.mongodb.db_name)
