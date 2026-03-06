"""Tool for retrieving the Blueprints business overview."""

from agents.blueprints.sub_agents.tool_factory import STORE_ROOT, create_file_tool

get_common_blueprint_info = create_file_tool(
    name="get_common_blueprint_info",
    description=(
        "Provides the high-level overview of what Blueprints is and how it works.\n\n"
        "Use this tool when you need to understand or answer questions about:\n"
        "- What Blueprints is and what problem it solves\n"
        "- Key concepts: workspaces, entity types, fields, tags, inheritance, naming stability\n"
        "- What users can configure through Blueprints\n"
        "- General practical limits (name lengths, field counts, tag limits)\n\n"
        "This is the starting point for any general 'what is Blueprints?' or 'what can I do?' question."
    ),
    file_path=STORE_ROOT / "common.md",
)
