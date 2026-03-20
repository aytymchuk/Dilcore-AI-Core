"""MongoDB-based checkpointer for LangGraph with per-tenant collections."""

from __future__ import annotations

import hashlib
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

# Cache of per-tenant MongoDBSavers keyed by resolved database name (no NoOp fallback cached).
_checkpointer_cache: dict[str, MongoDBSaver] = {}

# Max MongoDB database name length is 64 bytes; leave headroom for suffix.
_MONGO_DB_NAME_MAX = 63
_CHECKPOINT_DB_SUFFIX = "_langgraph_cp"
# ASCII hex suffix from original storage_identifier to avoid collisions after sanitization/truncation.
_STORAGE_ID_HASH_HEX_LEN = 8
_DEFAULT_CHECKPOINT_STORAGE_ID = "default"


def _storage_identifier_hash_suffix(storage_identifier: str) -> str:
    digest = hashlib.sha256(storage_identifier.encode("utf-8")).hexdigest()
    return digest[:_STORAGE_ID_HASH_HEX_LEN]


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
    """Human-readable ASCII-safe segment plus deterministic hash (avoids collisions after truncation).

    Layout: ``{truncated_readable}_{hash}{_CHECKPOINT_DB_SUFFIX}`` is built in
    :func:`_checkpoint_database_name`; this returns only ``{truncated_readable}_{hash}`` prefix
    before the fixed ``_langgraph_cp`` suffix.
    """
    # Disallowed in MongoDB DB names: / \ . " * < > : | ? $ and space (avoid oddities)
    cleaned = re.sub(r"[/\\.\"*<>:|?\s$]", "_", storage_identifier.strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_") or "default"
    # Alphanumeric + underscore only for the segment (ASCII-safe)
    cleaned = re.sub(r"[^a-zA-Z0-9_]", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_") or "default"
    # Reserve: '_' + hex hash + _CHECKPOINT_DB_SUFFIX (e.g. _a1b2c3d4_langgraph_cp)
    reserved = 1 + _STORAGE_ID_HASH_HEX_LEN + len(_CHECKPOINT_DB_SUFFIX)
    max_readable = _MONGO_DB_NAME_MAX - reserved
    if len(cleaned) > max_readable:
        cleaned = cleaned[:max_readable].rstrip("_") or "default"
    h = _storage_identifier_hash_suffix(storage_identifier)
    return f"{cleaned}_{h}"


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

    Each tenant/storage id gets its own MongoDB database (name:
    ``<sanitized_readable>_<hash8>_langgraph_cp``) with standard ``checkpoints`` /
    ``checkpoint_writes`` collections. Successful savers are cached in-memory; a
    failed ``MongoDBSaver`` init returns a non-cached ``NoOpCheckpointer`` so the next
    call can retry.
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
    except Exception:
        logger.exception(
            "MongoDBSaver init failed for db_name=%s; using no-op checkpointer (not cached)",
            db_name,
        )
        return NoOpCheckpointer()

    _checkpointer_cache[db_name] = saver
    return saver


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
