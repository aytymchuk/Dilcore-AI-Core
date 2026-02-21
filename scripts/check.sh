#!/usr/bin/env bash
# This script runs all poe checks (format, lint, typecheck, test)

echo "Running all code checks..."
uv run poe check
