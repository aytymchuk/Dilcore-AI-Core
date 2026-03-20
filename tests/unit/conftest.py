"""Unit-test fixtures — patches external services so no Docker/network is needed."""

from unittest.mock import patch

import pytest
from langgraph.checkpoint.memory import MemorySaver


@pytest.fixture(scope="session", autouse=True)
def mock_checkpointer():
    """Use in-memory checkpointer for graph compile and BlueprintsService thread APIs."""
    saver = MemorySaver()
    with patch(
        "infrastructure.checkpoint.document_checkpointer.get_checkpointer_for_storage_identifier",
        return_value=saver,
    ):
        yield saver
