"""Blueprints LangGraph runtime: compile supervisor graph with tenant-scoped checkpointer."""

from __future__ import annotations

from dataclasses import dataclass

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from agents.blueprints.nodes import (
    ASK_ROUTE,
    DESIGN_ROUTE,
    GENERATE_ROUTE,
    IDENTIFY_INTENT_ROUTE,
    IdentifyIntentNode,
    SupervisorNode,
)
from agents.blueprints.state import BlueprintsState
from agents.blueprints.sub_agents.ask.graph import build_ask_graph
from agents.blueprints.sub_agents.design.graph import build_design_graph
from agents.blueprints.sub_agents.generate.graph import build_generate_graph
from application.abstractions.abc_tenant_provider import AbcTenantProvider
from infrastructure.checkpoint.tenant_resolving_checkpointer import tenant_aware_checkpointer
from infrastructure.llm import create_llm
from shared.config import Settings


@dataclass(frozen=True, slots=True)
class BlueprintsRuntime:
    """Compiled supervisor graph and tenant-aware checkpointer (resolves collection per operation)."""

    compiled_graph: CompiledStateGraph
    checkpointer: BaseCheckpointSaver


def build_supervisor_state_graph(settings: Settings) -> StateGraph:
    """Build the StateGraph (nodes and edges) before compile."""
    llm = create_llm(settings, streaming=False)
    builder = StateGraph(BlueprintsState)

    builder.add_node("supervisor", SupervisorNode(llm))
    builder.add_node(ASK_ROUTE, build_ask_graph(settings))
    builder.add_node(DESIGN_ROUTE, build_design_graph(settings))
    builder.add_node(IDENTIFY_INTENT_ROUTE, IdentifyIntentNode())
    builder.add_node(GENERATE_ROUTE, build_generate_graph(settings))

    builder.add_edge(ASK_ROUTE, END)
    builder.add_edge(DESIGN_ROUTE, END)
    builder.add_edge(IDENTIFY_INTENT_ROUTE, END)
    builder.add_edge(GENERATE_ROUTE, END)

    builder.add_edge(START, "supervisor")
    return builder


def build_blueprints_runtime(
    settings: Settings,
    tenant_provider: AbcTenantProvider | None = None,
) -> BlueprintsRuntime:
    """Compile the Blueprints supervisor with a tenant-scoped checkpointer."""
    builder = build_supervisor_state_graph(settings)
    checkpointer = tenant_aware_checkpointer(tenant_provider)
    compiled = builder.compile(checkpointer=checkpointer)
    return BlueprintsRuntime(compiled_graph=compiled, checkpointer=checkpointer)
