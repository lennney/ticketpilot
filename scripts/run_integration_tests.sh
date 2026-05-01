#!/usr/bin/env bash
set -euo pipefail

echo "========================================="
echo "  TicketPilot Integration Tests"
echo "========================================="
echo ""

uv run python -m pytest tests/integration -v
