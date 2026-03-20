"""Request-scoped checkpointer: resolves the concrete saver on each BaseCheckpointSaver call."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from typing import Any

from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.base import BaseCheckpointSaver, CheckpointTuple

from application.abstractions.abc_tenant_provider import AbcTenantProvider

_SYNC_FORWARD = ("get_tuple", "list", "put", "put_writes", "delete_thread")
_ASYNC_FORWARD = ("aget_tuple", "aput", "aput_writes", "adelete_thread")


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

    async def alist(
        self,
        config: RunnableConfig | None,
        *,
        filter: dict[str, Any] | None = None,
        before: RunnableConfig | None = None,
        limit: int | None = None,
    ) -> AsyncIterator[CheckpointTuple]:
        inner = self._resolve()
        async for item in inner.alist(config, filter=filter, before=before, limit=limit):
            yield item


def _bind_sync(method_name: str):
    def _fn(self: TenantResolvingCheckpointer, *args: Any, **kwargs: Any) -> Any:
        return getattr(self._resolve(), method_name)(*args, **kwargs)

    return _fn


def _bind_async(method_name: str):
    async def _fn(self: TenantResolvingCheckpointer, *args: Any, **kwargs: Any) -> Any:
        method = getattr(self._resolve(), method_name)
        return await method(*args, **kwargs)

    return _fn


for _method in _SYNC_FORWARD:
    setattr(TenantResolvingCheckpointer, _method, _bind_sync(_method))

for _method in _ASYNC_FORWARD:
    setattr(TenantResolvingCheckpointer, _method, _bind_async(_method))


def tenant_aware_checkpointer(tenant_provider: AbcTenantProvider | None) -> TenantResolvingCheckpointer:
    """Factory: lazy-bind to ``document_checkpointer.get_checkpointer_for_tenant_provider`` (no import cycle)."""

    def _resolve_fn() -> BaseCheckpointSaver:
        from infrastructure.checkpoint import document_checkpointer as _doc

        return _doc.get_checkpointer_for_tenant_provider(tenant_provider)

    return TenantResolvingCheckpointer(_resolve_fn)
