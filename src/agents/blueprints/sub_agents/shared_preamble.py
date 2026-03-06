"""Shared preamble included in all sub-agent system prompts.

Explains the dual purpose of a Blueprint: no-code app configuration
AND semantic model for downstream AI agents.
"""

SEMANTIC_MODEL_PREAMBLE = """## Context: What is a Blueprint?

A Blueprint serves two critical purposes in the system:

1. **No-code application configuration** — It defines entities, fields, projections, views,
   workflows, and integrations that power a fully functional business application.
   Users configure (not code) their entire application through the Blueprint.

2. **Semantic model for downstream AI agents** — The same Blueprint acts as the semantic
   layer that other AI agents use to understand the business domain, interpret user
   requests, navigate data relationships, and generate context-aware responses.

This dual purpose means that every design decision matters beyond the immediate application:

- **Entity names and field descriptions** become the vocabulary that AI agents use to
  understand user queries. Clear, descriptive names enable better agent comprehension.
- **Relationships between entities** define how agents navigate between business concepts
  (e.g. knowing that a Deal belongs to a Customer lets an agent answer "show me all
  deals for Acme Corp").
- **Projections and views** define what perspectives on data agents can offer to users.
- **Validation rules and constraints** help agents understand what data is valid and
  provide better guidance.

The Blueprint is not just app configuration — it is the knowledge graph that powers
intelligent agent behavior across the entire platform."""
