"""Tool for retrieving agent behavior rules."""

from agents.blueprints.sub_agents.tool_factory import STORE_ROOT, create_file_tool

get_agent_rules = create_file_tool(
    name="get_agent_rules",
    description=(
        "Provides the behavior rules that govern how AI agents interact with Blueprints.\n\n"
        "Use this tool to understand the rules for generating valid output:\n"
        "- Schema integrity (never break schema name stability)\n"
        "- Validation compliance (payloads must satisfy all constraints)\n"
        "- Tenant isolation (operations scoped to single tenant)\n"
        "- Concurrency safety (eTag required on updates)\n"
        "- Business-to-API field type mapping\n"
        "- Completeness requirements (descriptions, tags)\n"
        "- Constraint awareness (limits on fields, nesting, names)\n"
        "- Semantic quality (clear naming for downstream AI agents)"
    ),
    file_path=STORE_ROOT / "agent-rules.md",
)
