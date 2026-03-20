"""MongoDB-based checkpointer for LangGraph with per-tenant collections."""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator, Iterator, Sequence
from typing import Any, NoReturn

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)
from langgraph.checkpoint.mongodb import MongoDBSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from pymongo import MongoClient

from application.abstractions.abc_tenant_provider import AbcTenantProvider
from application.domain.tenant import TenantInfo
from shared.config import get_settings
from shared.exceptions import AIAgentException

logger = logging.getLogger(__name__)

_mongo_client: MongoClient | None = None

# Cache of per-tenant MongoDBSavers keyed by resolved database name
_checkpointer_cache: dict[str, MongoDBSaver | NoOpCheckpointer] = {}

# Max MongoDB database name length is 64 bytes; leave headroom for suffix.
_MONGO_DB_NAME_MAX = 63
_CHECKPOINT_DB_SUFFIX = "_langgraph_cp"
_DEFAULT_CHECKPOINT_STORAGE_ID = "default"


def _storage_identifier_for_checkpointer(tenant_provider: AbcTenantProvider) -> str:
    """Resolve Mongo checkpoint DB segment from :meth:`AbcTenantProvider.get_tenant_info`."""
    try:
        tenant: TenantInfo = tenant_provider.get_tenant_info()
    except Exception as exc:
        # Log one line only; full traceback is emitted by the HTTP exception handler.
        logger.error(
            "Checkpointer: get_tenant_info() failed; cannot resolve storage identifier (%s: %s)",
            type(exc).__name__,
            exc,
        )
        raise

    sid = tenant.storage_identifier.strip()
    if not sid:
        raise ValueError("TenantInfo.storage_identifier is empty; cannot resolve checkpoint storage")
    return sid


def _sanitize_storage_id_for_db_name(storage_identifier: str) -> str:
    """Make ``storage_identifier`` safe for use as a MongoDB database name segment."""
    # Disallowed in MongoDB DB names: / \ . " * < > : | ? $ and space (avoid oddities)
    cleaned = re.sub(r"[/\\.\"*<>:|?\s$]", "_", storage_identifier.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_") or "default"
    # Alphanumeric + underscore only for the segment (ASCII-safe)
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_") or "default"
    max_segment = _MONGO_DB_NAME_MAX - len(_CHECKPOINT_DB_SUFFIX)
    if len(cleaned) > max_segment:
        cleaned = cleaned[:max_segment].rstrip("_") or "default"
    return cleaned


def _checkpoint_database_name(storage_identifier: str) -> str:
    """Dedicated database name for LangGraph checkpoints for this storage id."""
    return f"{_sanitize_storage_id_for_db_name(storage_identifier)}{_CHECKPOINT_DB_SUFFIX}"


# Compatibility shim: legacy API expected by some modules
def get_checkpointer() -> MongoDBSaver:
    """Return a default (global) MongoDBSaver for checkpoint persistence.

    This preserves backwards compatibility with code that imports
    get_checkpointer and uses it to persist LangGraph state without tenant scoping.
    The implementation falls back to the global MongoDB client and the default collection.
    """
    global _mongo_client  # noqa: PLW0603
    settings = get_settings()
    if _mongo_client is None:
        _mongo_client = MongoClient(settings.mongodb.connection_string)
    serde = JsonPlusSerializer(allowed_msgpack_modules=("agents.blueprints.models",))
    return MongoDBSaver(_mongo_client, db_name=settings.mongodb.db_name, serde=serde)


class NoOpCheckpointer(BaseCheckpointSaver):
    """A minimal no-op checkpointer used as a safe fallback when DB is unavailable."""

    def __init__(self, *args, **kwargs) -> None:
        pass

    def _raise(self) -> NoReturn:
        raise AIAgentException(
            problem_type="internal-error",
            title="Internal Server Error",
            status_code=500,
            message="Checkpoint DB unavailable",
        )

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        self._raise()

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        self._raise()

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        self._raise()

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        self._raise()

    def delete_thread(self, thread_id: str) -> None:
        self._raise()

    def delete_for_runs(self, run_ids: Sequence[str]) -> None:
        self._raise()

    def copy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
        self._raise()

    def prune(
        self,
        thread_ids: Sequence[str],
        *,
        strategy: str = "keep_latest",
    ) -> None:
        self._raise()

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        self._raise()

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        self._raise()

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        self._raise()

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        self._raise()

    async def adelete_thread(self, thread_id: str) -> None:
        self._raise()

    async def adelete_for_runs(self, run_ids: Sequence[str]) -> None:
        self._raise()

    async def acopy_thread(self, source_thread_id: str, target_thread_id: str) -> None:
        self._raise()

    async def aprune(
        self,
        thread_ids: Sequence[str],
        *,
        strategy: str = "keep_latest",
    ) -> None:
        self._raise()


def get_checkpointer_for_storage_identifier(storage_identifier: str) -> MongoDBSaver | NoOpCheckpointer:
    """Return a MongoDBSaver in a dedicated database derived from ``storage_identifier``.

    Each tenant/storage id gets its own MongoDB database (name: ``<sanitized>_langgraph_cp``)
    with standard ``checkpoints`` / ``checkpoint_writes`` collections. Savers are cached
    in-memory per database name.
    """
    if not storage_identifier:
        raise ValueError("storage_identifier must be a non-empty string")

    db_name = _checkpoint_database_name(storage_identifier)
    if db_name in _checkpointer_cache:
        return _checkpointer_cache[db_name]

    logger.debug(
        "Creating per-storage checkpointer: storage_identifier=%r -> db_name=%s",
        storage_identifier,
        db_name,
    )

    global _mongo_client
    settings = get_settings()
    if _mongo_client is None:
        _mongo_client = MongoClient(settings.mongodb.connection_string)

    serde = JsonPlusSerializer(allowed_msgpack_modules=("agents.blueprints.models",))
    try:
        saver = MongoDBSaver(
            _mongo_client,
            db_name=db_name,
            checkpoint_collection_name="checkpoints",
            writes_collection_name="checkpoint_writes",
            serde=serde,
        )
        used_saver = saver
    except Exception:
        logger.exception(
            "MongoDBSaver init failed for db_name=%s; using no-op checkpointer",
            db_name,
        )
        used_saver = NoOpCheckpointer()

    _checkpointer_cache[db_name] = used_saver
    return used_saver


def get_checkpointer_for_tenant_provider(
    tenant_provider: AbcTenantProvider | None,
) -> MongoDBSaver | NoOpCheckpointer:
    """Return the saver for ``tenant_provider``'s ``TenantInfo.storage_identifier`` (or ``default`` if no provider)."""
    storage_id = (
        _DEFAULT_CHECKPOINT_STORAGE_ID
        if tenant_provider is None
        else _storage_identifier_for_checkpointer(tenant_provider)
    )
    return get_checkpointer_for_storage_identifier(storage_id)


def close_checkpointer() -> None:
    """Close the underlying MongoClient and invalidate the cached saver."""
    global _mongo_client  # noqa: PLW0603
    if _mongo_client is not None:
        _mongo_client.close()
        _mongo_client = None
    # Clear per-collection saver cache on shutdown
    _checkpointer_cache.clear()
