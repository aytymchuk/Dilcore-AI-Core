"""Factory for creating file-backed LangChain tools.

All six blueprint reference tools (common, entity, field, agent-rules,
entity-api-reference, field-api-reference) follow an identical pattern:
resolve a markdown file path, read it, return its text.  This factory
eliminates that boilerplate.
"""

from __future__ import annotations

from pathlib import Path

from langchain_core.tools import tool

STORE_ROOT = Path(__file__).resolve().parents[3] / "store" / "files" / "blueprints"


def create_file_tool(name: str, description: str, file_path: Path):
    """Return a LangChain ``@tool`` that reads and returns *file_path* contents."""

    @tool(name, description=description)
    def _read_file() -> str:
        try:
            return file_path.read_text(encoding="utf-8")
        except Exception as e:
            return f"Error reading {file_path.name}: {e}"

    return _read_file
