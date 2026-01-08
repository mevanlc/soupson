#!/bin/bash
set -e

rm -rf .venv
find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
uv sync --reinstall
uv run soupson -h
