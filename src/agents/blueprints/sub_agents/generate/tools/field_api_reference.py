"""Tool for retrieving field definitions API reference."""

from agents.blueprints.sub_agents.tool_factory import STORE_ROOT, create_file_tool

get_field_api_reference = create_file_tool(
    name="get_field_api_reference",
    description=(
        "Returns the canonical fields API reference; use when you need exact API type names, "
        "nesting rules, or validation constraints — see fields-api-reference.md for full details."
    ),
    file_path=STORE_ROOT / "fields-api-reference.md",
)
