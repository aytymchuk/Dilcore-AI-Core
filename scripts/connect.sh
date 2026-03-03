#!/usr/bin/env bash
# This script opens a subshell with the Python virtual environment activated.

# Find the project root (parent directory of the scripts folder)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Virtual environment not found at $VENV_DIR"
    echo "Please run 'uv venv --python 3.12' to create it."
    exit 1
fi

echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"
echo "Virtual environment activated. Type 'exit' to leave."

# Replace the current shell process with the interactive shell
exec "$SHELL"
