# Tasks: Real LLM Provider Offline Comparison (Phase 12A)

## Phase Structure

Phase 12A is a focused batch with specific scope. Not a multi-sub-phase effort.

---

### Task 1 — OpenSpec Planning Layer

**Scope**: Create proposal.md, design.md, tasks.md, and spec file.

**Allowed files**:
- `openspec/changes/add-real-llm-provider-comparison/`

**Forbidden files**:
- `src/ticketpilot/` (no code changes)
- `tests/` (no test changes)
- `data/` (no data changes)

**Validation**:
```bash
openspec validate add-real-llm-provider-comparison --strict
openspec validate --all
uv run ruff check .
```

---

### Task 2 — OpenAI-Compatible Provider Implementation

**Scope**: Add OpenAICompatibleProvider to provider_config.py and llm_provider.py.

**Allowed files**:
- `src/ticketpilot/drafting/provider_config.py` (extend)
- `src/ticketpilot/drafting/llm_provider.py` (extend)
- `openspec/changes/add-real-llm-provider-comparison/` (update tasks.md)
- `docs/changelog.md`
- `docs/harness/`

**Forbidden files**:
- `src/ticketpilot/retrieval/` (no retrieval changes)
- `data/` (no data changes)
- `.env`, `.env.local`

**Validation**:
```bash
uv run pytest tests/unit/test_openai_compatible_llm_provider.py -v --tb=short
openspec validate add-real-llm-provider-comparison --strict
uv run ruff check .
```

---

### Task 3 — Mock Unit Tests

**Scope**: Add mock tests for OpenAICompatibleProvider. Must NOT call network.

**Allowed files**:
- `tests/unit/test_openai_compatible_llm_provider.py` (new)
- `openspec/changes/add-real-llm-provider-comparison/` (update tasks.md)
- `docs/changelog.md`
- `docs/harness/`

**Forbidden files**:
- `data/` (no data changes)

**Validation**:
```bash
uv run pytest tests/unit/test_openai_compatible_llm_provider.py -v --tb=short
```

---

### Task 4 — Comparison Fixture Set

**Scope**: Create synthetic fixture set for offline comparison.

**Allowed files**:
- `tests/fixtures/phase12_draft_comparison_cases.json` (new)
- `openspec/changes/add-real-llm-provider-comparison/` (update tasks.md)
- `docs/changelog.md`
- `docs/harness/`

**Forbidden files**:
- `data/eval/` (Phase 7/8/9/10/11 baselines frozen)
- `src/ticketpilot/` (no code changes)

**Validation**:
```bash
uv run ruff check tests/fixtures/phase12_draft_comparison_cases.json
```

---

### Task 5 — Comparison Runner

**Scope**: Add scripts/run_phase12_llm_provider_comparison.py.

**Allowed files**:
- `scripts/run_phase12_llm_provider_comparison.py` (new)
- `openspec/changes/add-real-llm-provider-comparison/` (update tasks.md)
- `docs/changelog.md`
- `docs/harness/`

**Forbidden files**:
- `src/ticketpilot/` (no code changes)
- `data/eval/` (frozen)

**Validation**:
```bash
python scripts/run_phase12_llm_provider_comparison.py --help
```

---

### Task 6 — Runner Integration Tests

**Scope**: Add tests/integration/test_phase12_llm_provider_comparison.py.

**Allowed files**:
- `tests/integration/test_phase12_llm_provider_comparison.py` (new)
- `openspec/changes/add-real-llm-provider-comparison/` (update tasks.md)
- `docs/changelog.md`
- `docs/harness/`

**Forbidden files**:
- `data/eval/` (frozen)

**Validation**:
```bash
uv run pytest tests/integration/test_phase12_llm_provider_comparison.py -v --tb=short
```

---

### Task 7 — Report Generation and Docs

**Scope**: Generate comparison reports and technical documentation.

**Allowed files**:
- `reports/eval/phase12_llm_provider_comparison_*.json` (new)
- `reports/eval/phase12_llm_provider_comparison_report.md` (new)
- `docs/technical/phase12_real_provider_comparison.md` (new)
- `openspec/changes/add-real-llm-provider-comparison/` (update tasks.md)
- `docs/changelog.md`
- `docs/harness/`

**Forbidden files**:
- `src/ticketpilot/` (no code changes)
- `data/eval/` (frozen)
- `reports/retrieval/` (frozen)

**Validation**:
```bash
python scripts/run_phase12_llm_provider_comparison.py --limit 5
```

---

### Task 8 — Full Validation and Archive

**Scope**: Run full quality gate, archive OpenSpec change, update harness docs.

**Allowed files**:
- `openspec/changes/add-real-llm-provider-comparison/` (final updates)
- `openspec/changes/archive/` (archive destination)
- `docs/changelog.md`
- `docs/harness/`
- `reports/harness/`

**Forbidden files**:
- `src/ticketpilot/` (no code changes)
- `tests/` (no test changes)
- `data/` (no data changes)
- `reports/retrieval/` (frozen)
- `.env`, `.env.local`

**Validation**:
```bash
bash scripts/run_quality_gate.sh
openspec validate add-real-llm-provider-comparison --strict
openspec validate --all
uv run ruff check .
grep -r "sk-" data/ --include="*.csv"
```

**Stop conditions**:
- Full quality gate fails after 2 repairs
- Integration tests skipped > 0 with DB available
- Secret scan fails
- API key appears in git diff