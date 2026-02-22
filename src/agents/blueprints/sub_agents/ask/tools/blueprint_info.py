"""Tool for retrieving blueprint configuration information."""

from langchain_core.tools import tool


@tool
def get_blueprint_configuration_info() -> str:
    """Provides overall information about the blueprint configuration and data structural layer.

    Use this tool when you need to understand or answer questions about:
    - How blueprints are structured
    - Entity properties (identity, inheritance, etc.)
    - Available field types and complex objects (Object, Array)
    - Relationship metadata
    - Constraints and Indices

    This is the definitive guide to what a blueprint is and its constraints.
    """
    try:
        with open("src/store/files/blueprints/common.md", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading blueprint configuration: {e}"
