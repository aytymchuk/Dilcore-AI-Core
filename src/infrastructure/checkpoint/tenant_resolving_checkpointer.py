"""Request-scoped checkpointer: resolves the concrete saver on each BaseCheckpointSaver call."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Iterator, Sequence
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import (
    BaseCheckpointSaver,
    ChannelVersions,
    Checkpoint,
    CheckpointMetadata,
    CheckpointTuple,
)

from application.abstractions.abc_tenant_provider import AbcTenantProvider


class TenantResolvingCheckpointer(BaseCheckpointSaver):
    """Delegates every checkpoint API call to ``resolve_saver()`` (per-request tenant DB)."""

    def __init__(self, resolve_saver: Callable[[], BaseCheckpointSaver]) -> None:
        super().__init__()
        self._resolve_saver = resolve_saver

    def _resolve(self) -> BaseCheckpointSaver:
        return self._resolve_saver()

    @property
    def config_specs(self) -> list:
        return self._resolve().config_specs

    def get_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return self._resolve().get_tuple(config)

    def list(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,  # noqa: A002
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> Iterator[CheckpointTuple]:
        return self._resolve().list(config, filter=filter, before=before, limit=limit)

    def put(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        return self._resolve().put(config, checkpoint, metadata, new_versions)

    def put_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        return self._resolve().put_writes(config, writes, task_id, task_path=task_path)

    def delete_thread(self, thread_id: str) -> None:
        return self._resolve().delete_thread(thread_id)

    async def aget_tuple(self, config: RunnableConfig) -> CheckpointTuple | None:
        return await self._resolve().aget_tuple(config)

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,  # noqa: A002
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        inner = self._resolve()
        async for item in inner.alist(config, filter=filter, before=before, limit=limit):
            yield item

    async def aput(
        self,
        config: RunnableConfig,
        checkpoint: Checkpoint,
        metadata: CheckpointMetadata,
        new_versions: ChannelVersions,
    ) -> RunnableConfig:
        return await self._resolve().aput(config, checkpoint, metadata, new_versions)

    async def aput_writes(
        self,
        config: RunnableConfig,
        writes: Sequence[tuple[str, Any]],
        task_id: str,
        task_path: str = "",
    ) -> None:
        return await self._resolve().aput_writes(config, writes, task_id, task_path=task_path)

    async def adelete_thread(self, thread_id: str) -> None:
        return await self._resolve().adelete_thread(thread_id)


def tenant_aware_checkpointer(tenant_provider: AbcTenantProvider | None) -> TenantResolvingCheckpointer:
    """Factory: lazy-bind to ``document_checkpointer.get_checkpointer_for_tenant_provider`` (no import cycle)."""

    def _resolve_fn() -> BaseCheckpointSaver:
        from infrastructure.checkpoint import document_checkpointer as _doc

        return _doc.get_checkpointer_for_tenant_provider(tenant_provider)

    return TenantResolvingCheckpointer(_resolve_fn)
