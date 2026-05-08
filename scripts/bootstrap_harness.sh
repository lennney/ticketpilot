#!/bin/bash
# TicketPilot Controller Harness Bootstrap Script
# 
# Purpose: Verify harness environment is set up correctly on new machine or clone.
# Usage: bash scripts/bootstrap_harness.sh [--check|--setup]

set -e

HARNESS_DIR="docs/harness"
SKILLS_DIR="docs/harness/skills"
SUBAGENT_RESULTS_DIR="subagent_results"
REPORTS_HARNESS_DIR="reports/harness"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_bootstrap() {
    echo "=== Controller Harness Bootstrap Check ==="
    echo ""
    
    local all_ok=true
    
    # Check 1: Core harness files exist
    echo "1. Checking core harness files..."
    if [[ -f "AGENTS.md" ]] && [[ -f "$HARNESS_DIR/PHASE_LOOP.md" ]] && [[ -f "$HARNESS_DIR/PROJECT_CONTEXT.md" ]]; then
        echo -e "${GREEN}[OK]${NC} Core files present: AGENTS.md, PHASE_LOOP.md, PROJECT_CONTEXT.md"
    else
        echo -e "${RED}[FAIL]${NC} Missing core files"
        all_ok=false
    fi
    
    # Check 2: Skills directory
    echo ""
    echo "2. Checking skills directory..."
    if [[ -d "$SKILLS_DIR" ]]; then
        local skill_count=$(find "$SKILLS_DIR" -name "*.md" ! -name "TEMPLATE.md" | wc -l)
        echo -e "${GREEN}[OK]${NC} Skills directory exists ($skill_count skills)"
    else
        echo -e "${YELLOW}[WARN]${NC} Skills directory not found (will be created on first use)"
    fi
    
    # Check 3: Subagent results directory
    echo ""
    echo "3. Checking subagent results directory..."
    if [[ -d "$SUBAGENT_RESULTS_DIR" ]]; then
        local result_count=$(find "$SUBAGENT_RESULTS_DIR" -name "*.md" 2>/dev/null | wc -l)
        echo -e "${GREEN}[OK]${NC} Subagent results directory exists ($result_count results)"
    else
        echo -e "${YELLOW}[INFO]${NC} Subagent results directory will be created on first phase"
    fi
    
    # Check 4: Reports directory
    echo ""
    echo "4. Checking reports/harness directory..."
    if [[ -d "$REPORTS_HARNESS_DIR" ]]; then
        echo -e "${GREEN}[OK]${NC} Reports directory exists"
    else
        echo -e "${YELLOW}[INFO]${NC} Reports directory will be created on first error/phase"
    fi
    
    # Check 5: .claude/CLAUDE.md exists (auto-loaded by Claude Code)
    echo ""
    echo "5. Checking .claude/CLAUDE.md (Claude Code auto-loads this)..."
    if [[ -f ".claude/CLAUDE.md" ]]; then
        echo -e "${GREEN}[OK]${NC} .claude/CLAUDE.md exists (harness bootstrap info included)"
    else
        echo -e "${RED}[FAIL]${NC} .claude/CLAUDE.md missing"
        all_ok=false
    fi
    
    # Check 6: Project dependencies
    echo ""
    echo "6. Checking project dependencies..."
    if command -v uv &> /dev/null; then
        echo -e "${GREEN}[OK]${NC} uv installed"
    else
        echo -e "${RED}[FAIL]${NC} uv not found (install: https://github.com/astral-sh/uv)"
        all_ok=false
    fi
    
    if [[ -d ".venv" ]]; then
        echo -e "${GREEN}[OK]${NC} Virtual environment exists"
    else
        echo -e "${YELLOW}[WARN]${NC} Virtual environment not found (run: uv sync)"
    fi
    
    # Summary
    echo ""
    echo "=== Bootstrap Status ==="
    if $all_ok; then
        echo -e "${GREEN}Harness is ready!${NC}"
        echo ""
        echo "To start Controller Mode, human can say:"
        echo "  - 'Start phase N from tasks.md'"
        echo "  - 'Run controller harness for [task]'"
        echo "  - 'Enter controller mode'"
        echo ""
        echo "Key files:"
        echo "  - AGENTS.md: Core rules (read first)"
        echo "  - docs/harness/PHASE_LOOP.md: 7-step workflow"
        echo "  - docs/harness/PROJECT_CONTEXT.md: Current state"
        return 0
    else
        echo -e "${RED}Harness bootstrap incomplete.${NC}"
        echo "Run: bash scripts/bootstrap_harness.sh --setup"
        return 1
    fi
}

setup_bootstrap() {
    echo "=== Setting up Controller Harness ==="
    echo ""
    
    # Create directories if missing
    mkdir -p "$HARNESS_DIR/skills"
    mkdir -p "$SUBAGENT_RESULTS_DIR"
    mkdir -p "$REPORTS_HARNESS_DIR"
    
    echo "Created directories:"
    echo "  - $HARNESS_DIR/skills/"
    echo "  - $SUBAGENT_RESULTS_DIR/"
    echo "  - $REPORTS_HARNESS_DIR/"
    
    # Check for skills template
    if [[ ! -f "$SKILLS_DIR/TEMPLATE.md" ]]; then
        echo ""
        echo -e "${YELLOW}Note: No skills template found.${NC}"
        echo "Template will be created from PHASE_LOOP.md on first skill codification."
    fi
    
    echo ""
    echo -e "${GREEN}Setup complete!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. uv sync  (if not done)"
    echo "2. docker compose up -d  (for integration tests)"
    echo "3. Say 'start controller harness' to enter Controller Mode"
}

# Main
case "${1:-}" in
    --check)
        check_bootstrap
        ;;
    --setup)
        setup_bootstrap
        ;;
    "")
        check_bootstrap
        ;;
    *)
        echo "Usage: $0 [--check|--setup]"
        echo "  --check  Verify harness setup (default)"
        echo "  --setup  Create missing directories"
        exit 1
        ;;
esac
