#!/usr/bin/env bash
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

FAILED=0

echo "========================================="
echo "  TicketPilot Quality Gate"
echo "========================================="

# 1. Ruff linting
echo ""
echo "== Ruff =="
uv run ruff check src tests || {
    echo -e "${RED}FAIL: Ruff linting errors found${NC}"
    FAILED=1
}

# 2. Unit tests
echo ""
echo "== Unit Tests =="
# Remove stale coverage data from previous runs (WSL cross-filesystem SQLite corruption)
rm -f /tmp/.coverage* .coverage* 2>/dev/null || true
# Resolve coverage directory to Windows-absolute path when Python runs on Windows
COVERAGE_DIR="$(uv run python -c "import tempfile; print(tempfile.gettempdir())" 2>/dev/null || echo "/tmp")"
export COVERAGE_FILE="${COVERAGE_FILE:-${COVERAGE_DIR}/.coverage_ticketpilot_gate}"
uv run python -m pytest tests/unit/ -v --strict-markers --cov=src/ticketpilot --cov-fail-under=70 || {
    echo -e "${RED}FAIL: Unit tests failed${NC}"
    FAILED=1
}

# 3. Integration tests (with skip-count guard)
echo ""
echo "== Integration Tests =="
set +e
INTEGRATION_OUTPUT=$(uv run python -m pytest tests/integration/ -v --strict-markers 2>&1)
INTEGRATION_EXIT=$?
set -e

SKIPPED_COUNT=$(echo "$INTEGRATION_OUTPUT" | grep -o '[0-9]* skipped' | grep -o '[0-9]*' || echo "0")
SKIPPED_COUNT=${SKIPPED_COUNT:-0}
echo "$INTEGRATION_OUTPUT" | tail -25

if [ "${TICKETPILOT_SKIP_DB_TESTS:-0}" = "1" ]; then
    echo -e "${YELLOW}INFO: TICKETPILOT_SKIP_DB_TESTS=1, allowing ${SKIPPED_COUNT} skipped tests${NC}"
elif [ "$SKIPPED_COUNT" -gt 0 ]; then
    echo -e "${RED}FAIL: ${SKIPPED_COUNT} integration tests skipped (DB unavailable).${NC}"
    echo -e "${RED}      Set TICKETPILOT_SKIP_DB_TESTS=1 to temporarily allow.${NC}"
    FAILED=1
elif [ "$INTEGRATION_EXIT" -ne 0 ]; then
    echo -e "${RED}FAIL: Integration tests failed${NC}"
    FAILED=1
fi

# 4. OpenSpec validation
echo ""
echo "== OpenSpec Validation =="
if command -v openspec >/dev/null 2>&1; then
    openspec validate --all || {
        echo -e "${RED}FAIL: OpenSpec validation failed${NC}"
        FAILED=1
    }
else
    echo -e "${YELLOW}WARNING: OpenSpec not installed, skipping${NC}"
fi

# 5. Secret scan
echo ""
echo "== Secret Scan =="
if grep -rP 'sk-[a-zA-Z0-9]{20,}' . \
    --exclude-dir=.git \
    --exclude-dir=.venv \
    --exclude-dir=.venv_broken \
    --exclude='.env.example' \
    --exclude='.env.local' \
    2>/dev/null; then
    echo -e "${RED}FAIL: Potential secret detected${NC}"
    FAILED=1
else
    echo "No obvious OpenAI-style secret found."
fi

echo ""
echo "========================================="
if [ "$FAILED" -eq 0 ]; then
    echo -e "${GREEN}  Quality Gate PASSED${NC}"
    echo "========================================="
    exit 0
else
    echo -e "${RED}  Quality Gate FAILED${NC}"
    echo "========================================="
    exit 1
fi
