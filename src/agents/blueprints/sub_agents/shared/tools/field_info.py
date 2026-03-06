"""Tool for retrieving field types and structure business knowledge."""

from agents.blueprints.sub_agents.tool_factory import STORE_ROOT, create_file_tool

get_field_info = create_file_tool(
    name="get_field_info",
    description=(
        "Provides business-level knowledge about field types and structure.\n\n"
        "Use this tool when you need to understand or answer questions about:\n"
        "- What fields are and how they define the data an entity carries\n"
        "- Available field types explained in business terms:\n"
        "    * Simple: Text, Number, Yes/No, Date and Time, File, Reference\n"
        "    * Structured: Group (bundled sub-fields), List (repeating items)\n"
        "- How to choose the right field type based on what the data means\n"
        "- How structured fields work (nesting, groups, lists with examples)\n"
        "- Practical limits: nesting depth, field counts per level\n"
        "- Why clear field naming matters for users and AI agents\n\n"
        "This explains fields from a business perspective — no technical API details."
    ),
    file_path=STORE_ROOT / "fields.md",
)
