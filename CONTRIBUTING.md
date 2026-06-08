# Contributing to TicketPilot

Thanks for your interest in contributing! Here's how to get started.

## Development Setup

```bash
git clone https://github.com/lennney/ticketpilot.git
cd ticketpilot
pip install uv
uv sync --group dev
docker compose up -d db
```

## Running Tests

```bash
# Unit tests (no DB required, fast)
TICKETPILOT_SKIP_DB_TESTS=1 uv run pytest tests/ --ignore=tests/integration -q

# Full tests (requires DB)
uv run pytest tests/ -v

# Quality gate (must pass before PR)
bash scripts/run_quality_gate.sh
```

## Code Style

- **Linter**: ruff (all rules enabled, no isort)
- **Type hints**: Required for all public functions
- **Docstrings**: Required for all public modules and classes
- **Tests**: Every new feature needs tests; coverage must stay ≥ 70%

## How to Contribute

### Reporting Bugs

Open an issue with:
- Steps to reproduce
- Expected vs actual behavior
- Python version and OS

### Submitting Changes

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Make your changes with tests
4. Run the quality gate: `bash scripts/run_quality_gate.sh`
5. Submit a PR with a clear description

### Good First Issues

Look for issues labeled `good-first-issue`:

- 📝 Documentation improvements
- 🧪 Test coverage for edge cases
- 🔧 Small bug fixes
- 🌐 Internationalization

## Architecture Notes

The pipeline is **deterministic by design** — no LLM calls in the core pipeline
(classification, risk, retrieval, confidence scoring). LLM is only used in
`DraftAgent` for reply generation. This is intentional: it means the pipeline
is fully testable without mocking LLM responses.

## Questions?

Open a discussion or comment on an existing issue.
