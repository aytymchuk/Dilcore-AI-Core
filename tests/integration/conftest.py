"""Integration-test fixtures — real MongoDB via testcontainers."""

from unittest.mock import patch

import pytest
from langgraph.checkpoint.mongodb import MongoDBSaver
from pymongo import MongoClient
from testcontainers.mongodb import MongoDbContainer


@pytest.fixture(scope="session")
def mongodb_container():
    """Start a disposable MongoDB container for the test session."""
    with MongoDbContainer() as mongo:
        yield mongo


@pytest.fixture(scope="session")
def mongodb_checkpointer(mongodb_container):
    """Create a MongoDBSaver backed by the testcontainer instance."""
    connection_string = mongodb_container.get_connection_url()
    client = MongoClient(connection_string)
    return MongoDBSaver(client, db_name="test_langgraph_checkpoints")


@pytest.fixture(autouse=True)
def patch_checkpointer(mongodb_checkpointer):
    """Route get_checkpointer() to the testcontainer-backed saver for every integration test."""
    with patch(
        "infrastructure.checkpoint.document_checkpointer.get_checkpointer",
        return_value=mongodb_checkpointer,
    ):
        yield
