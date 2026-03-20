#!/usr/bin/env bash
# This script bootstraps a Python virtual environment (if missing), installs
# dependencies, and runs the app in a live development server.

# Find the project root (parent directory of the scripts folder)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

set -euo pipefail

install_dependencies() {
  echo "Installing/upgrading Python dependencies..."
  # Upgrade pip first
  "$VENV_DIR/bin/python" -m pip install --upgrade pip >/dev/null 2>&1 || true
  # Install dependencies from pyproject.toml in editable mode for development
  "$VENV_DIR/bin/pip" install --upgrade -e "$PROJECT_ROOT"
}

if [ ! -d "$VENV_DIR" ]; then
  echo "Virtual environment not found at $VENV_DIR. Creating..."
  # Try to use python3.12 if available, otherwise fall back to python3
  if command -v python3.12 >/dev/null 2>&1; then
    python3.12 -m venv "$VENV_DIR"
  else
    python3 -m venv "$VENV_DIR"
  fi
fi

if [ ! -f "$VENV_DIR/bin/activate" ]; then
  echo "Failed to activate venv (missing $VENV_DIR/bin/activate). Aborting."
  exit 1
fi

echo "Activating virtual environment..."
# shellcheck disable=SC1090
source "$VENV_DIR/bin/activate"

install_dependencies

echo "Starting the app on http://0.0.0.0:8080..."
uvicorn src.main:app --reload --port 8080 --host 0.0.0.0
