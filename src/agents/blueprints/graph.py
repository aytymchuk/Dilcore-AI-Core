"""Blueprints LangGraph — public surface and LangGraph Studio lazy export."""

from __future__ import annotations

from typing import Any

from agents.blueprints.runtime import BlueprintsRuntime, build_blueprints_runtime
from application.abstractions.abc_tenant_provider import AbcTenantProvider
from shared.config import Settings


class BlueprintsGraph:
    """Thin façade over a compiled LangGraph and its checkpointer."""

    def __init__(self, runtime: BlueprintsRuntime) -> None:
        self._runtime = runtime

    async def ainvoke(self, state: dict | Any, config: dict | None = None) -> dict:
        return await self._runtime.compiled_graph.ainvoke(state, config=config)

    async def aget_state(self, config: dict) -> Any:
        return await self._runtime.compiled_graph.aget_state(config)


def create_blueprints_graph(
    settings: Settings,
    tenant_provider: AbcTenantProvider | None = None,
) -> Any:
    """Build the compiled supervisor graph (optional tenant for checkpointer scope)."""
    return build_blueprints_runtime(settings, tenant_provider).compiled_graph


# Lazy entrypoint for LangGraph Studio / CLI
_graph = None


def __getattr__(name: str):
    """Lazily construct the compiled graph on first access."""
    global _graph
    if name == "graph":
        if _graph is None:
            from container import get_app_container

            _graph = get_app_container().agents.blueprints_runtime().compiled_graph
        return _graph
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
