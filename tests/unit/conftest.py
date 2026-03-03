"""Unit-test fixtures — patches external services so no Docker/network is needed."""

from unittest.mock import patch

import pytest
from langgraph.checkpoint.memory import MemorySaver


@pytest.fixture(scope="session", autouse=True)
def mock_checkpointer():
    """Replace the MongoDB checkpointer with an in-memory saver for all unit tests."""
    saver = MemorySaver()
    with patch(
        "infrastructure.checkpoint.document_checkpointer.get_checkpointer",
        return_value=saver,
    ):
        yield saver


@pytest.fixture(autouse=True)
def _reset_service_singleton():
    """Reset the BlueprintsService module-level singleton between tests."""
    import api.controllers.dependencies as deps

    deps._blueprints_service = None
    yield
    deps._blueprints_service = None
