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
  # Core server dependencies (adjust as needed)
  "$VENV_DIR/bin/pip" install --upgrade \
    uvicorn[standard]>=0.34.0 \
    fastapi[standard]>=0.115.0 \
    scalar-fastapi==1.6.1 \
    sse-starlette>=2.1.0,<2.2.0 \
    httpx>=0.27.0 \
    pydantic-settings>=2.0.0 \
    python-dotenv>=1.0.0 \
    langchain>=0.3.27 \
    langgraph>=0.2.83 \
    pymongo>=4.12,<4.16 \
    cryptography>=44.0.0 \
    PyJWT>=2.10.1
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

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

if [ ! -f "$VENV_DIR/bin/activate" ]; then
  echo "Failed to activate venv. Aborting."
  exit 1
fi

install_dependencies || true

echo "Starting the app on http://0.0.0.0:8080..."
uvicorn src.main:app --reload --port 8080 --host 0.0.0.0
