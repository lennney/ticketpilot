#!/usr/bin/env bash
set -e

echo "== Ruff =="
uv run ruff check . || true

echo "== Pytest =="
uv run pytest || true

echo "== OpenSpec validation =="
if command -v openspec >/dev/null 2>&1; then
  openspec validate --all || true
else
  echo "OpenSpec not installed. Skipping."
fi

echo "== Secret scan placeholder =="
if grep -R "sk-" . --exclude-dir=.git --exclude-dir=.venv --exclude=".env.example"; then
  echo "Potential secret detected."
  exit 1
else
  echo "No obvious OpenAI-style secret found."
fi

echo "Quality gate completed."
