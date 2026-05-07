# Tasks: Extended Draft Evaluation Metrics

## Task 13.1 — OpenSpec Planning

**Status**: DONE (Phase 13.1)

OpenSpec change `add-extended-draft-evaluation-metrics` created with:
- `proposal.md`, `design.md`, `tasks.md` (this file)
- `specs/draft-evaluation-metrics/spec.md`, `specs/provider-comparison-metrics/spec.md`, `specs/reviewer-ready-metric/spec.md`
- All specs validated with `## ADDED Requirements` delta headers and SHALL/MUST language

---

## Task 13.2 — Extend Metric Computation Module

**Status**: DONE (already implemented in Phase 11.8)

All metric functions and schemas were implemented in Phase 11.8:
- `src/ticketpilot/evaluation/draft_metrics.py` — `compute_citation_precision()`, `compute_evidence_coverage()`, `compute_human_review_trigger_correct()`, `compute_draft_evaluation_summary()`
- `src/ticketpilot/evaluation/schemas.py` — `DraftEvaluationRow`, `DraftEvaluationSummary`
- `tests/unit/test_draft_metrics.py` — 32 comprehensive tests (all passing)

---

## Task 13.3 — Extend Provider Comparison Runner

**Status**: DONE

Modified `scripts/run_phase12_llm_provider_comparison.py`:
- Added `--extended-rows` flag to output `DraftEvaluationRow` JSON
- Integrated `generate_draft()` with proper `TicketOutput` construction
- Serialized per-case: citation_validation.is_valid, valid/invalid/available evidence counts, guard_passed, forbidden_promise_count, unsupported_claim_count
- Computed `DraftEvaluationSummary` from rows via `compute_draft_evaluation_summary()`
- All 25 cases successful with citation precision=1.0, guard_pass_rate=0.0, human_review_accuracy=1.0

**Validation**: Run with `--limit 3` verified extended fields in output JSON

---

## Task 13.4 — Add Unit Tests for Extended Metrics

**Status**: DONE (already implemented in Phase 11.8)

Unit tests for all metric functions exist in `tests/unit/test_draft_metrics.py` (32 tests).
Tests cover: citation_precision, evidence_coverage, human_review_trigger_correct,
unsupported_claim_rate, forbidden_promise_rate, guard_pass_rate, citation_validation_pass_rate,
serialization, and None handling.

---

## Task 13.5 — Regenerate Fake Baseline with Extended Metrics

**Status**: DONE

- Ran `scripts/run_phase12_llm_provider_comparison.py --extended-rows` with FakeLLMProvider
- Generated `reports/eval/phase12_llm_provider_comparison_rows.json` with 25 `DraftEvaluationRow` objects
- Generated `reports/eval/phase12_llm_provider_comparison_summary.json` with full `DraftEvaluationSummary`
- Citation precision: 1.0, guard_pass_rate: 0.0, human_review_accuracy: 1.0
- Real provider not run (env not configured); can be added via `.env.local`

---

## Task 13.6 — Update Portfolio Docs

**Status**: TODO

Update:
- `docs/portfolio/ticketpilot_metrics_dashboard.md`: replace not-yet-measured with actual values from Phase 13
- `docs/portfolio/phase12_provider_comparison_analysis.md`: add citation precision, evidence coverage, guard pass rate, unsupported claim rate, forbidden promise rate
- `docs/portfolio/phase12_reviewer_ready_metric.md`: mark as implemented; compute from Phase 13 data; update data gap section
- `docs/portfolio/phase12_error_analysis.md`: add Phase 13 measurement coverage update

**Allowed files**:
- `docs/portfolio/ticketpilot_metrics_dashboard.md`
- `docs/portfolio/phase12_provider_comparison_analysis.md`
- `docs/portfolio/phase12_reviewer_ready_metric.md`
- `docs/portfolio/phase12_error_analysis.md`

**Forbidden files**:
- Archived Phase 7/8/9/10/11 portfolio snapshots
- Archived Phase 7/8/9/10/11 reports

**Validation**: `openspec validate --all`

---

## Task 13.7 — Final Validation and Archive

**Status**: TODO

- Run full quality gate: `bash scripts/run_quality_gate.sh` (or `TICKETPILOT_SKIP_DB_TESTS=1` if DB unavailable)
- Run: `openspec validate add-extended-draft-evaluation-metrics --strict`
- Run: `openspec validate --all`
- Run: `uv run ruff check .`
- Run secret scan: verify no API keys in git diff
- Run overclaim scan: verify boundary wording on all new/updated reports
- Archive: `openspec archive add-extended-draft-evaluation-metrics`
- Update harness docs: changelog, controller context, next actions, session log, engineering log, validation log

**Validation commands**:
```bash
bash scripts/run_quality_gate.sh  # or TICKETPILOT_SKIP_DB_TESTS=1
openspec validate add-extended-draft-evaluation-metrics --strict
openspec validate --all
uv run ruff check .
```

**Required checks**:
- Unit tests: all pass
- Integration tests: all pass (0 skipped if DB available)
- Coverage: ≥70%
- Ruff: clean
- OpenSpec: all valid
- Secret scan: clean
- Overclaim scan: clean
- Boundary wording: present in all new/updated reports
