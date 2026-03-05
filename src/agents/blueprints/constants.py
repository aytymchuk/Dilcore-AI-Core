"""Centralized constants for the Blueprints agent graph.

All route names, agent type literals, and phase types live here to
avoid duplication across supervisor, state, and sub-agent modules.
"""

from __future__ import annotations

from typing import Literal

# ---------------------------------------------------------------------------
# Route names used by the supervisor to dispatch to sub-graphs / nodes
# ---------------------------------------------------------------------------
ASK_ROUTE = "ask"
DESIGN_ROUTE = "design"
GENERATE_ROUTE = "generate"
IDENTIFY_INTENT_ROUTE = "identify_intent"

ALL_ROUTES = {ASK_ROUTE, DESIGN_ROUTE, GENERATE_ROUTE, IDENTIFY_INTENT_ROUTE}

RouteNames = Literal["ask", "design", "generate", "identify_intent"]

# ---------------------------------------------------------------------------
# Agent type identifiers stamped onto AI messages via middleware / tagging
# ---------------------------------------------------------------------------
ASK_AGENT: Literal["ask"] = "ask"
DESIGN_AGENT: Literal["design"] = "design"
GENERATE_AGENT: Literal["generate"] = "generate"

AgentType = Literal["ask", "design", "generate"]

# ---------------------------------------------------------------------------
# Phase type — superset of AgentType that includes identify_intent and empty
# ---------------------------------------------------------------------------
PhaseType = Literal["ask", "design", "generate", "identify_intent", ""]
