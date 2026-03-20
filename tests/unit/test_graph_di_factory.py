from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import container as container_module
from agents.blueprints import graph as graph_module


class DummyProvider:
    def __init__(self):
        self._tenant = SimpleNamespace(storage_identifier="tenant123")

    def get_tenant_info(self):
        return self._tenant


def test_create_blueprints_graph_passes_tenant_provider_to_runtime(monkeypatch):
    captured: dict[str, Any] = {}

    def fake_build(settings: Any, tenant_provider: Any = None):
        captured["tenant_provider"] = tenant_provider
        return SimpleNamespace(compiled_graph="COMPILED", checkpointer="CP")

    # Patch graph's bound reference (imported at module load).
    monkeypatch.setattr(graph_module, "build_blueprints_runtime", fake_build)

    settings: Any = SimpleNamespace()
    dummy_provider = DummyProvider()
    result = graph_module.create_blueprints_graph(settings, tenant_provider=dummy_provider)

    assert result == "COMPILED"
    assert captured["tenant_provider"] is dummy_provider


def test_graph_attribute_uses_container_runtime(monkeypatch):
    sentinel = object()

    class FakeAgents:
        def blueprints_runtime(self):
            return SimpleNamespace(compiled_graph=sentinel)

    class FakeRoot:
        agents = FakeAgents()

    monkeypatch.setattr(container_module, "get_app_container", lambda: FakeRoot())
    monkeypatch.setattr(graph_module, "_graph", None)
    assert graph_module.graph is sentinel
