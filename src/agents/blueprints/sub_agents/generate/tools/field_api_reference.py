"""Tool for retrieving field definitions API reference."""

from agents.blueprints.sub_agents.tool_factory import STORE_ROOT, create_file_tool

get_field_api_reference = create_file_tool(
    name="get_field_api_reference",
    description=(
        "Provides the full technical API reference for field definitions.\n\n"
        "Use this tool when you need to produce valid field payloads including:\n"
        "- Field JSON structure (schemaName, displayName, type, nested fields)\n"
        "- Exact API type names: String, Number, Boolean, DateTime, File, Identifier, Object, Array\n"
        "- Business-to-API type mapping (what users say vs. the API type to use)\n"
        "- Nesting rules for Object and Array types\n"
        "- Schema name generation, immutability, and reserved names\n"
        "- Validation constraints (name lengths, nesting depth, fields per level)"
    ),
    file_path=STORE_ROOT / "fields-api-reference.md",
)
