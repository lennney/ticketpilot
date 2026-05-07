# Validation Log -- TicketPilot

---

## 2026-05-07 -- Phase 13.10.1: Final Validation and Archive — Guard-Aware Prompting

| Check | Result |
|---|---|
| Ruff | All checks passed |
| Unit tests (prompt builder) | 59 passed |
| Unit tests (draft generator) | 33 passed |
| Unit tests (claim guard) | 58 passed |
| Full quality gate | 1078 unit + 146 integration, 0 skipped, coverage 86.56% |
| OpenSpec --all | 24/24 passed |
| Secret scan | Clean |
| Overclaim scan | Clean — all matches in appropriate boundary/negative contexts |
| OpenSpec archive | add-guard-aware-provider-prompting → 2026-05-07-add-guard-aware-provider-prompting |
| Spec promoted | openspec/specs/guard-aware-prompting/spec.md |
| OpenSpec --all after archive | 24/24 passed |

**Phase 13.10 real provider metrics confirmed**:
- Citation validation pass: 12% → 76%
- Claim guard pass: 4% → 84%
- Reviewer-ready rate: 4% → 64%
- Remaining 4 failures: correct guard behavior (risk escalation, unsupported claims, forbidden promises)
- Boundary: offline fixture-based, not benchmark, not production

**Status**: PASSED — archive commit is clean baseline (985349e confirmed)

---

## 2026-05-07 -- Phase 13.9.1: Validation Closure — Strict Full Quality Gate

| Check | Result |
|---|---|
| Ruff | All checks passed |
| Unit tests | 1069 passed |
| Integration tests | 146 passed, 0 skipped |
| Coverage | 87% (>= 70% threshold) |
| OpenSpec --all | 23/23 passed |
| Secret scan | Clean |
| Docs-only batch | Full quality gate not required (Phase 13.9 focused validation) |
| Strict full gate | Run on top of Phase 13.9 to establish clean baseline |

**Phase 13.9 had**: ruff, OpenSpec, 65 draft unit tests — passed. Full gate was not run (docs/portfolio-only batch).
**Phase 13.9.1 ran**: `scripts/run_quality_gate.sh` on top of 0e050d6 — passed.

**Phase 13.9 key metrics confirmed**:
- Fake citation validation pass: 100% (25/25)
- Real citation validation pass: 12% (3/25)
- Fake claim guard pass: 68% (17/25)
- Real claim guard pass: 4% (1/25)
- Real unsupported claim rate: 88% (22/25)
- Real human review triggers: 100% (25/25)

**Status**: PASSED — 0e050d6 is confirmed clean baseline.

---

## 2026-05-07 -- Phase 13.9: Real Provider Extended Comparison Run

| Check | Result |
|---|---|
| Ruff | All checks passed |
| Fake provider extended rows | 25/25, citation_precision=1.0, guard_pass_rate=0.68 |
| Real provider extended rows | 25/25, citation_precision=1.0, guard_pass_rate=0.04 |
| Fake citation validation pass | 25/25 (100%) |
| Real citation validation pass | 3/25 (12%) |
| Fake unsupported claim rate | 0% (0/25) |
| Real unsupported claim rate | 88% (22/25) |
| Fake human review triggers | 8/25 (32%) |
| Real human review triggers | 25/25 (100%) |
| Script bug fix | Added missing `actual_human_review` field to `result_dict` |
| Portfolio docs | Updated metrics dashboard and reviewer-ready metric doc |
| OpenSpec --all | 23/23 passed |
| Docs-only batch | Full quality gate not required (strict gate run separately in Phase 13.9.1) |

**Root cause of real provider low guard/citation-valid rates**: Real LLM (deepseek-v4-pro) generates short free-form Chinese text (80–174 chars) without inline `[chunk_id]` citation markers. The claim guard's content-level check flags `has_uncited_claims=True` for substantive text without markers. Citation validator's structural check also fails because no `[uuid]` markers exist in text. This is an expected behavior for a free-form LLM without guard-aware prompting. No auto-send. Human review required for all cases.

**Status**: PASSED — Real provider metrics now available; portfolio docs updated

## 2026-05-07 -- Phase 12D.1: Resolve Untracked OpenSpec Spec Directory

| Check | Result |
|---|---|
| Ruff | All checks passed |
| OpenSpec --all | 23/23 passed (22 before + 1 new spec added) |
| Spec-only cleanup | Full quality gate not required |

**Status**: PASSED

---

## 2026-05-07 -- Phase 13: Extended Draft Evaluation Metrics (Planning)

| Check | Result |
|---|---|
| Ruff | All checks passed |
| OpenSpec --strict (add-extended-draft-evaluation-metrics) | Valid |
| OpenSpec --all | 23/23 passed |
| Docs/spec-only batch | Full quality gate not required |

**Status**: PASSED

---

## 2026-05-07 -- Phase 13.2: Metric Functions (Already Implemented in Phase 11.8)

| Check | Result |
|---|---|
| Source code | `draft_metrics.py` already exists from Phase 11.8 |
| Schemas | `DraftEvaluationRow`/`DraftEvaluationSummary` already exist from Phase 11.8 |
| Tests | `test_draft_metrics.py` already exists (32 tests) |
| Validation | 32/32 passed |

**Status**: PASSED — No new implementation needed; all components from Phase 11.8

---

## 2026-05-07 -- Phase 13.3: Extend Provider Comparison Runner

| Check | Result |
|---|---|
| Ruff | All checks passed |
| Script update | `run_phase12_llm_provider_comparison.py` extended with `--extended-rows` |
| `generate_draft()` | Integrated with `TicketOutput` construction |
| `DraftEvaluationRow` | Serialization from `DraftGenerationResult` fields |
| Test run | 25/25 successful |
| Extended rows output | `phase12_extended_eval_rows_*.json` generated |
| Summary metrics | citation_precision=1.0, guard_pass_rate=0.0, human_review_accuracy=1.0 |
| Unit tests | `test_draft_metrics.py` 32/32 passed, `test_draft_generator.py` 33/33 passed |

**Status**: PASSED — Runner now produces extended `DraftEvaluationRow` JSON with full citation and guard metrics

---

## 2026-05-07 -- Phase 13.8: Guard Metric Interpretation and Fix

| Check | Result |
|---|---|
| Root cause | FakeLLMProvider used `[N]` numeric markers instead of `[UUID]` chunk_id markers |
| Citation validation | Passed (cited_evidence_ids correct, only text markers wrong) |
| Claim guard | Failed (no UUID markers found → has_uncited_claims=True) |
| Fix | Updated FakeLLMProvider template to use `[{ev.chunk_id}]` format |
| After fix | guard_pass_rate=68% (17/25), remaining failures are HIGH-severity cases |
| Severity propagation | Added HIGH severity → must_human_review in generator.py |
| Test isolation | Added `TICKETPILOT_LLM_PROVIDER=fake` to conftest.py |
| Ruff | All checks passed |
| Unit tests | 123/123 passed (33 draft_generator + 32 draft_metrics + 58 claim_guard) |
| OpenSpec --all | 23/23 passed |
| Quality gate | PASSED |

**Status**: PASSED

*Tracks validation runs, quality gate results, and test outcomes.*

---

## 2026-05-07 -- Phase 12D: Metrics Dashboard and Portfolio Evidence Pack

| Check | Result |
|---|---|
| Ruff | All checks passed |
| OpenSpec --all | 22/22 passed |
| Docs-only batch | Full quality gate not required |

**Status**: PASSED — Docs/portfolio-only batch, no runtime changes

---

## 2026-05-07 -- Phase 12C.2: Strict Quality Gate Restoration

| Check | Result |
|---|---|
| Ruff | All checks passed |
| Unit tests | 1069 passed |
| Integration tests | 146 passed, **0 skipped** |
| Coverage | 86.71% (>=70%) |
| OpenSpec --all | 21/21 passed |
| Secret scan | Clean |
| Overclaim scan | Clean |
| Real provider configured | NO |
| Real provider run | NO (env missing) |
| Fake baseline | 25/25 cases, avg confidence 0.85, 8 human review |

**Status**: PASSED — Phase 12C complete, real provider pending local env

---

## 2026-05-07 -- Phase 12B: Agent Error Memory and Repair Learning System

| Check | Result |
|---|---|
| OpenSpec --strict (add-agent-error-memory-system) | Valid |
| OpenSpec --all | 21/21 passed |
| Ruff | All checks passed |
| Secret scan | Clean |
| Overclaim scan | Clean |
| Docs-only batch | No quality gate required |

---

, quality gate results, and test outcomes.*

---

## 2026-05-07 — Phase 12A.1: Real LLM Provider Comparison Validation Closure

| Check | Result |
|---|---|
| Ruff | All checks passed |
| Unit tests | 1069 passed |
| Integration tests | 146 passed, **0 skipped** |
| Coverage | 86.71% (>=70%) |
| OpenSpec --all | 20/20 passed |
| Secret scan | Clean |
| Comparison runner | Fake baseline: 5/5 cases successful |
| Real provider | Not configured |

**Status**: PASSED - Phase 12A validation closed, real provider pending local env

---

# Validation Log — TicketPilot

*Tracks validation runs, quality gate results, and test outcomes.*

---

## 2026-05-06 — Phase 11.10: Final Validation and Archive

| Check | Result |
|---|---|
| Ruff | All checks passed |
| Unit tests | 1001 passed |
| Integration tests | 140 passed, **0 skipped** |
| Coverage | ≥70% threshold passed |
| OpenSpec --strict (add-evidence-grounded-llm-draft) | Valid |
| OpenSpec --all | 19/19 passed (post-archive) |
| Secret scan | Clean |
| Overclaim scan | Clean |
| OpenSpec archive | ✅ `add-evidence-grounded-llm-draft` → `archive/2026-05-06-*` |

**Status**: ✅ PASSED

---

## 2026-05-06 — Phase 11.9: Portfolio Snapshot

| Check | Result |
|---|---|
| Ruff | All checks passed |
| Unit tests | 1001 passed (32 new draft metrics tests) |
| Integration tests | 126 passed (7 new draft eval runner tests), **0 skipped** |
| OpenSpec --all | 17/17 passed |
| Draft eval script | 10 cases completed, rows/summary/md generated |
| Secret scan | Clean |

**Status**: ✅ PASSED

---

| Check | Result |
|---|---|
| Ruff | All checks passed |
| Unit tests | 807 passed |
| Integration tests | 119 passed, **0 skipped** |
| Coverage | 85.74% (≥70%) |
| OpenSpec --all | 17/17 passed |
| Secret scan | Clean |

**Status**: ✅ PASSED

---

## 2026-05-06 — Phase 11.3: Full Quality Gate

| Check | Result |
|---|---|
| Ruff | All checks passed |
| Unit tests | 857 passed (50 new prompt builder tests) |
| Integration tests | 119 passed, **0 skipped** |
| Coverage | 86.04% (≥70%) |
| OpenSpec --all | 17/17 passed |
| Secret scan | Clean |
| Overclaim scan | Clean |

**Status**: ✅ PASSED

---

## 2026-05-06 — Phase 11.4: Full Quality Gate

| Check | Result |
|---|---|
| Ruff | All checks passed |
| Unit tests | 878 passed (21 new draft citation validator tests) |
| Integration tests | 119 passed, **0 skipped** |
| Coverage | 86.35% (≥70%) |
| OpenSpec --all | 17/17 passed |
| Secret scan | Clean |
| Overclaim scan | Clean |

**Status**: ✅ PASSED

---

## 2026-05-06 — Phase 11.5: Module Tests

| Check | Result |
|---|---|
| Unit tests (test_claim_guard.py) | 58/58 passed |
| Ruff | ✅ Clean |
| OpenSpec --strict (add-evidence-grounded-llm-draft) | ✅ Passed |
| OpenSpec --all | ✅ 17/17 passed |

**Status**: ✅ PASSED

---

## 2026-05-06 — Phase 11.6: Pipeline Integration

| Check | Result |
|---|---|
| Unit tests (test_draft_generator.py) | 33/33 passed |
| Integration tests (test_draft_generation_integration.py) | 14/14 passed |
| Ruff | ✅ Clean |
| OpenSpec --strict (add-evidence-grounded-llm-draft) | ✅ Passed |
| OpenSpec --all | ✅ 17/17 passed |

**Status**: ✅ PASSED

---

## 2026-05-06 — Phase 11.1: OpenSpec Planning Validation

| Check | Result |
|---|---|
| OpenSpec --strict (add-evidence-grounded-llm-draft) | ✅ Passed |
| OpenSpec --all | ✅ 17/17 passed |
| Ruff | ✅ All checks passed |

**Status**: ✅ PASSED

---

## 2026-05-06 — Phase 10.9: Full Quality Gate (Final)

| Check | Result |
|---|---|
| Ruff | All checks passed |
| Unit tests | 778 passed |
| Integration tests | 119 passed, **0 skipped** |
| Coverage | 85.27% (≥70%) |
| OpenSpec --all | 16/16 passed |
| Secret scan | Clean |
| Overclaim scan | Clean |

**Status**: ✅ PASSED

---

## 2026-05-06 — Phase 10.7.5: Module Tests

| Test suite | Count | Result |
|---|---|---|
| test_retrieval_metrics | 40/40 | ✅ |
| test_evaluation* | 103/103 | ✅ |
| Ruff check | — | ✅ Clean |

**Status**: ✅ PASSED

---

## 2026-05-06 — Phase 10.8: Validation

| Check | Result |
|---|---|
| Ruff | ✅ Clean |
| openspec --strict | ✅ |
| openspec --all | ✅ |

**Status**: ✅ PASSED
