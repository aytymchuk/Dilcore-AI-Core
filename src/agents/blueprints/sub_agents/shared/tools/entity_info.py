"""Tool for retrieving entity definition business knowledge."""

from agents.blueprints.sub_agents.tool_factory import STORE_ROOT, create_file_tool

get_entity_info = create_file_tool(
    name="get_entity_info",
    description=(
        "Provides business-level knowledge about Entity Definitions.\n\n"
        "Use this tool when you need to understand or answer questions about:\n"
        "- What an entity type is and real-world examples (CRM, HR, Operations, Finance)\n"
        "- What makes up an entity: name, description, fields, tags, inheritance\n"
        "- What actions users can perform: create, update, browse, view, remove\n"
        "- Naming rules, field update behavior, version safety\n"
        "- Why descriptions matter for both users and AI agents\n\n"
        "This explains entities from a business perspective — no technical API details."
    ),
    file_path=STORE_ROOT / "entities.md",
)
