# Tasks: Extended Draft Evaluation Metrics

## Task 13.1 — OpenSpec Planning

**Status**: TODO

- [ ] Create OpenSpec change `add-extended-draft-evaluation-metrics`
- [ ] Write proposal.md
- [ ] Write design.md
- [ ] Write tasks.md
- [ ] Write specs/draft-evaluation-metrics/spec.md
- [ ] Write specs/provider-comparison-metrics/spec.md
- [ ] Write specs/reviewer-ready-metric/spec.md
- [ ] Validate scoped: `openspec validate add-extended-draft-evaluation-metrics --strict`
- [ ] Validate full: `openspec validate --all`

**Allowed files**:
- `openspec/changes/add-extended-draft-evaluation-metrics/**`

**Forbidden files**:
- Any `src/`, `tests/`, `scripts/`, `data/` modifications
- Archived OpenSpec changes
- Archived Phase 7/8/9/10/11 reports

**Validation**: `openspec validate add-extended-draft-evaluation-metrics --strict`

---

## Task 13.2 — Extend Metric Computation Module

**Status**: TODO

Create `src/ticketpilot/evaluation/draft_comparison_metrics.py` with pure metric functions:
- `citation_precision()`
- `evidence_coverage()`
- `unsupported_claim_rate()`
- `forbidden_promise_rate()`
- `guard_pass_rate()`
- `citation_validation_pass_rate()`
- `reviewer_ready_rate()`
- `hr_trigger_metrics()`

**Allowed files**:
- `src/ticketpilot/evaluation/draft_comparison_metrics.py` (new)
- `src/ticketpilot/evaluation/__init__.py` (exports)

**Forbidden files**:
- No retrieval, RRF, embedding, chunking, knowledge, golden label modifications
- No real LLM API calls
- No auto-send logic

**Validation**: `uv run pytest tests/unit/test_draft_comparison_metrics.py -v`

---

## Task 13.3 — Extend Provider Comparison Runner

**Status**: TODO

Modify `scripts/run_phase12_llm_provider_comparison.py`:
- Call `generate_draft()` and extract full `DraftGenerationResult`
- Serialize per-case: citation_validation.is_valid, valid/invalid/available evidence IDs, guard_passed, has_forbidden_promise, has_uncited_claims, unsupported_claims, reviewer_ready flag, latency if available
- Output extended rows JSON with all new fields
- Compute summary metrics from extended rows

**Allowed files**:
- `scripts/run_phase12_llm_provider_comparison.py` (modify)

**Forbidden files**:
- No retrieval, RRF, embedding, chunking, knowledge, golden label modifications
- No real LLM API calls (real provider opt-in only via .env.local)

**Validation**: Run with `--limit 3` to verify extended fields appear in output

---

## Task 13.4 — Add Unit Tests for Extended Metrics

**Status**: TODO

Create `tests/unit/test_draft_comparison_metrics.py`:
- Test citation_precision with: valid citations, invalid citations, no citations, no evidence
- Test evidence_coverage with: partial coverage, full coverage, no evidence
- Test unsupported_claim_rate with: no claims, some claims, all claims
- Test forbidden_promise_rate with: no promises, some promises, all promises
- Test guard_pass_rate with: all passed, mixed, none passed
- Test citation_validation_pass_rate with: all valid, some invalid, none valid
- Test reviewer_ready_rate with: all ready, some ready, none ready
- Test high-risk + guard-pass case: should be reviewer-ready AND must_human_review

**Allowed files**:
- `tests/unit/test_draft_comparison_metrics.py` (new)

**Forbidden files**:
- No runtime code changes
- No integration test changes

**Validation**: `uv run pytest tests/unit/test_draft_comparison_metrics.py -v --tb=short`

---

## Task 13.5 — Regenerate Fake Baseline and Optional Real Provider Comparison

**Status**: TODO

- Run `scripts/run_phase12_llm_provider_comparison.py` with fake provider
- Regenerate `reports/eval/phase12_llm_provider_comparison_rows.json` with extended fields
- Regenerate `reports/eval/phase12_llm_provider_comparison_summary.json` with all new metrics
- Regenerate `reports/eval/phase12_llm_provider_comparison_report.md` with metric tables
- If `.env.local` has real provider configured: run real provider comparison
- Verify: all new metrics are computed and non-null where applicable

**Allowed files**:
- `reports/eval/phase12_llm_provider_comparison_*.json` (overwrite)
- `reports/eval/phase12_llm_provider_comparison_report.md` (overwrite)
- `.env.local` (not committed)

**Forbidden files**:
- Archived Phase 7/8/9/10/11 reports
- No retrieval, RRF, embedding, chunking, knowledge modifications

**Validation**: Inspect output JSON for new metric fields

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
