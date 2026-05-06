# Tasks: Evidence-Grounded LLM Draft Generation (Phase 11)

## Phase Structure

Phase 11 is divided into 10 sub-phases. Each sub-phase is a self-contained batch with its own allowed/forbidden files and validation commands.

---

### 11.1 — OpenSpec Planning Layer

**Scope**: Create proposal, design, task breakdown, and 4 spec files.

**Allowed files**:
- `openspec/changes/add-evidence-grounded-llm-draft/`
- `docs/changelog.md`
- `docs/harness/`
- `reports/harness/`

**Forbidden files**:
- `src/ticketpilot/` (no code changes)
- `tests/` (no test changes)
- `data/` (no data changes)
- `reports/retrieval/` (Phase 7/8/9/10 reports frozen)
- `docs/portfolio/` (portfolio docs frozen)
- `openspec/changes/archive/` (archived changes frozen)

**Validation**:
```bash
openspec validate add-evidence-grounded-llm-draft --strict
openspec validate --all
uv run ruff check .
```

**Stop conditions**:
- Any src/ or tests/ file modified
- Any data/ file modified
- Archived report modified
- Openspec validation fails after one repair

---

### 11.2 — Draft Schema and Deterministic Provider ✅

**Scope**: Implement LLM provider interface, FakeLLMProvider, and extend DraftReply schema.

**Allowed files**:
- `src/ticketpilot/drafting/llm_provider.py` (new)
- `src/ticketpilot/drafting/provider_config.py` (new)
- `src/ticketpilot/drafting/schemas.py` (extend DraftReply)
- `tests/unit/test_llm_provider.py` (new)
- `tests/unit/test_drafting_schemas.py` (extend if needed)
- `openspec/changes/add-evidence-grounded-llm-draft/` (update tasks.md)
- `docs/changelog.md`
- `docs/harness/`

**Forbidden files**:
- `src/ticketpilot/retrieval/` (no retrieval changes)
- `data/` (no data changes)
- `reports/retrieval/` (frozen)
- `docs/portfolio/` (frozen)
- `.env`, `.env.local`

**Validation**:
```bash
uv run pytest tests/unit/test_llm_provider.py tests/unit/test_drafting_schemas.py -v --tb=short
openspec validate add-evidence-grounded-llm-draft --strict
uv run ruff check .
```

**Stop conditions**:
- Real LLM API called
- Retrieval algorithm modified
- Knowledge data modified
- Golden labels modified

---

### 11.3 — Evidence-Grounded Prompt Builder

**Scope**: Implement prompt builder that converts evidence candidates + ticket context into structured LLM prompts.

**Allowed files**:
- `src/ticketpilot/drafting/prompt_builder.py` (new)
- `tests/unit/test_prompt_builder.py` (new)
- `openspec/changes/add-evidence-grounded-llm-draft/` (update tasks.md)
- `docs/changelog.md`
- `docs/harness/`

**Forbidden files**:
- `src/ticketpilot/retrieval/` (no retrieval changes)
- `data/` (no data changes)
- `reports/retrieval/` (frozen)

**Validation**:
```bash
uv run pytest tests/unit/test_prompt_builder.py -v --tb=short
openspec validate add-evidence-grounded-llm-draft --strict
uv run ruff check .
```

---

### 11.4 — Citation Validator Extension

**Scope**: Extend existing CitationValidator to handle LLM-generated draft output (stricter citation checking, chunk_id format validation).

**Allowed files**:
- `src/ticketpilot/drafting/citation_validator.py` (extend)
- `tests/unit/test_citation_validator.py` (extend)
- `openspec/changes/add-evidence-grounded-llm-draft/`
- `docs/changelog.md`
- `docs/harness/`

**Forbidden files**:
- `src/ticketpilot/retrieval/` (no retrieval changes)
- `data/` (no data changes)
- `reports/retrieval/` (frozen)

**Validation**:
```bash
uv run pytest tests/unit/test_citation_validator.py -v --tb=short
openspec validate add-evidence-grounded-llm-draft --strict
uv run ruff check .
```

---

### 11.5 — Unsupported-Claim Guard

**Scope**: Implement ClaimGuard with citation coverage check, forbidden promise detection, risk-aware check.

**Allowed files**:
- `src/ticketpilot/drafting/claim_guard.py` (new)
- `tests/unit/test_claim_guard.py` (new)
- `openspec/changes/add-evidence-grounded-llm-draft/`
- `docs/changelog.md`
- `docs/harness/`

**Forbidden files**:
- `src/ticketpilot/retrieval/` (no retrieval changes)
- `data/` (no data changes)
- `reports/retrieval/` (frozen)

**Validation**:
```bash
uv run pytest tests/unit/test_claim_guard.py -v --tb=short
openspec validate add-evidence-grounded-llm-draft --strict
uv run ruff check .
```

---

### 11.6 — Pipeline Integration

**Scope**: Wire LLM provider, prompt builder, and claim guard into `generate_draft()`. Update `generate.py` and `schemas.py`. Ensure end-to-end flow works with FakeLLMProvider.

**Allowed files**:
- `src/ticketpilot/drafting/generate.py` (modify)
- `src/ticketpilot/drafting/schemas.py` (extend if needed)
- `src/ticketpilot/drafting/__init__.py` (update exports)
- `src/ticketpilot/pipeline.py` (minimal changes if needed)
- `tests/unit/test_drafting_generate.py` (extend)
- `tests/unit/test_pipeline.py` (extend)
- `tests/integration/test_draft_generation.py` (new)
- `openspec/changes/add-evidence-grounded-llm-draft/`
- `docs/changelog.md`
- `docs/harness/`

**Forbidden files**:
- `src/ticketpilot/retrieval/` (no retrieval changes)
- `data/` (no data changes)
- `reports/retrieval/` (frozen)

**Validation**:
```bash
uv run pytest tests/unit/test_drafting_generate.py tests/unit/test_pipeline.py -v --tb=short
uv run pytest tests/integration/test_draft_generation.py -v --tb=short
openspec validate add-evidence-grounded-llm-draft --strict
uv run ruff check .
```

**Stop conditions**:
- Integration tests fail or skip > 0 with DB
- Pipeline behavior changes for non-draft stages

---

### 11.7 — Human Review Console Update

**Scope**: Update Streamlit console to display guard results, provider_id, escalation_reason. Extend ReviewDecision schema.

**Allowed files**:
- `src/ticketpilot/review/schemas.py` (extend ReviewDecision)
- `src/ticketpilot/review/console.py` (extend display)
- `tests/unit/test_review_*.py` (extend)
- `openspec/changes/add-evidence-grounded-llm-draft/`
- `docs/changelog.md`
- `docs/harness/`

**Forbidden files**:
- `src/ticketpilot/retrieval/` (no retrieval changes)
- `data/` (no data changes)
- `reports/retrieval/` (frozen)

**Validation**:
```bash
uv run pytest tests/unit/test_review_*.py -v --tb=short
openspec validate add-evidence-grounded-llm-draft --strict
uv run ruff check .
```

---

### 11.8 — Offline Draft Evaluation

**Scope**: Implement draft quality metrics: citation precision, evidence coverage, unsupported claim rate, safe fallback rate, human review trigger correctness. Add golden expectations for draft metrics.

**Allowed files**:
- `src/ticketpilot/evaluation/draft_metrics.py` (new)
- `src/ticketpilot/evaluation/schemas.py` (extend GoldenExpectation)
- `src/ticketpilot/evaluation/metrics.py` (integrate draft metrics)
- `tests/unit/test_draft_metrics.py` (new)
- `tests/unit/test_evaluation_*.py` (extend)
- `data/eval/golden_expectations.csv` (append draft columns only)
- `openspec/changes/add-evidence-grounded-llm-draft/`
- `docs/changelog.md`
- `docs/harness/`

**Forbidden files**:
- `src/ticketpilot/retrieval/` (no retrieval changes)
- `reports/retrieval/` (frozen)
- Existing golden columns (append only, never modify)

**Validation**:
```bash
uv run pytest tests/unit/test_draft_metrics.py tests/unit/test_evaluation_*.py -v --tb=short
openspec validate add-evidence-grounded-llm-draft --strict
uv run ruff check .
```

---

### 11.9 — Portfolio Snapshot

**Scope**: Create `docs/portfolio/phase11_evidence_draft_snapshot.md` with before/after comparison, architecture diagram, key design decisions. Update existing portfolio docs with Phase 11 references.

**Allowed files**:
- `docs/portfolio/phase11_evidence_draft_snapshot.md` (new)
- `docs/portfolio/ticketpilot_product_case_onepager.md` (append-only)
- `docs/portfolio/product_portfolio_material_pack.md` (update next-steps)
- `README.md` (update Phase 11 references)
- `README.en.md` (update Phase 11 references)
- `docs/changelog.md`
- `docs/harness/`
- `reports/harness/`

**Forbidden files**:
- `src/ticketpilot/` (no code changes)
- `tests/` (no test changes)
- `data/` (no data changes)
- `reports/retrieval/` (frozen)
- Prior phase portfolio snapshots (immutable)

**Validation**:
```bash
uv run ruff check .
openspec validate add-evidence-grounded-llm-draft --strict
openspec validate --all
```

---

### 11.10 — Final Validation and Archive

**Scope**: Run full quality gate, archive OpenSpec change, update all harness docs.

**Allowed files**:
- `openspec/changes/add-evidence-grounded-llm-draft/` (final updates)
- `openspec/changes/archive/` (archive destination)
- `docs/changelog.md`
- `docs/harness/`
- `reports/harness/`

**Forbidden files**:
- `src/ticketpilot/` (no code changes)
- `tests/` (no test changes)
- `data/` (no data changes)
- `reports/retrieval/` (frozen)
- `docs/portfolio/` (frozen — snapshot already created in 11.9)
- `.env`, `.env.local`

**Validation**:
```bash
bash scripts/run_quality_gate.sh
openspec validate add-evidence-grounded-llm-draft --strict
openspec validate --all
uv run ruff check .
grep -r "sk-" data/ --include="*.csv"
```

**Stop conditions**:
- Full quality gate fails after 2 repairs
- Integration tests skipped > 0 with DB available
- Forbidden files modified
- Secret scan fails
- Archived reports modified
