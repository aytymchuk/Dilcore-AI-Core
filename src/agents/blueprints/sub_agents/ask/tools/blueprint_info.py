"""Tool for retrieving blueprint configuration information."""

from pathlib import Path

from langchain_core.tools import tool

_BLUEPRINT_DOCS_PATH = Path(__file__).resolve().parents[5] / "store" / "files" / "blueprints" / "common.md"


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
        return _BLUEPRINT_DOCS_PATH.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading blueprint configuration: {e}"
