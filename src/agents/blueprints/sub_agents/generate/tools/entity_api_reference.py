"""Tool for retrieving entity definitions API reference."""

from agents.blueprints.sub_agents.tool_factory import STORE_ROOT, create_file_tool

get_entity_api_reference = create_file_tool(
    name="get_entity_api_reference",
    description=(
        "Provides the full technical API reference for Entity Definitions.\n\n"
        "Use this tool when you need to produce valid API payloads for:\n"
        "- Creating entity definitions (POST request body, required/optional properties)\n"
        "- Updating entity definitions (PUT request body, eTag requirement, field replacement behavior)\n"
        "- Listing entity definitions (query parameters for pagination, search, filtering)\n"
        "- Understanding the full JSON structure of an entity definition\n"
        "- Schema name generation rules (camelCase conversion, immutability, reserved names)\n"
        "- Validation constraints (name lengths, field limits, tag rules, regex patterns)\n"
        "- Error formats (400 validation, 404 not found, 409 conflict/eTag mismatch)"
    ),
    file_path=STORE_ROOT / "entities-api-reference.md",
)
