# TicketPilot Metrics Dashboard

**Scope**: Local demo / portfolio prototype — NOT a production benchmark
**Last updated**: 2026-05-08

---

## 1. Dataset and Knowledge Base

| Metric | Value | Source |
|--------|-------|--------|
| Synthetic eval tickets | 101 | `data/eval/tickets_eval.csv` |
| Cases with doc-level labels | 86 / 101 (85.1%) | `reports/retrieval/phase10_full_real_doc_level_eval_metrics.json` |
| Knowledge records | 106 total | `data/knowledge/faq_seed.json`, `policy_seed.json`, `case_seed.json` |
| — FAQ records | 41 | same sources |
| — Policy records | 34 | same sources |
| — Case records | 31 | same sources |
| Knowledge chunks (estimated) | ~140 | `src/ticketpilot/retrieval/db/seeding.py` chunking logic |

---

## 2. Retrieval Evaluation

| Metric | Value | Source |
|--------|-------|--------|
| Doc-Type Recall@10 | 59.4% (59/101) | `phase10_full_real_doc_level_eval_metrics.json` |
| Doc-ID Recall@10 | 91.9% (79/86 labeled) | same |
| Doc-Type MRR | 0.4995 | same |
| Doc-ID MRR | 0.4881 | same |
| Doc-Type Recall@1 | 44.6% | same |
| Doc-ID Recall@1 | 30.2% | same |
| Wrong cases (doc-type) | 41 / 101 | same |
| Reclassified as doc-id found | 32 / 41 (78%) | same — metric granularity |
| Still wrong at doc-id level | 9 | same — genuine misses |
| Zero-hit cases (doc-id) | 9 | same |
| Partial-hit cases | 32 | same |
| Cases fully correct at top-10 | 47 / 86 (54.7%) | same |

**Source**: `reports/retrieval/phase10_full_real_doc_level_eval_metrics.json`
**Boundary**: Offline evaluation on 101 synthetic tickets — not a production benchmark. Pipeline verification only — no semantic retrieval quality.

---

## 3. Draft Generation Evaluation

### Phase 13.10: Guard-Aware Prompting Results (2026-05-07)

| Metric | FakeLLMProvider | Real Provider (deepseek-v4-pro, guard-aware) | Source |
|--------|-----------------|----------------------------------------------|--------|
| Citation precision | 100% (25/25) | 100% (25/25) | Phase 13.10 extended |
| Citation validation pass rate | 100% (25/25) | 76% (19/25) | Phase 13.10 extended |
| Claim guard pass rate | 68% (17/25) | 84% (21/25) | Phase 13.10 extended |
| Unsupported claim rate | 0% (0/25) | 24% (6/25) | Phase 13.10 extended |
| Forbidden promise rate | 0% (0/25) | 4% (1/25) | Phase 13.10 extended |
| Safe fallback rate | 0% (0/25) | 84% (21/25) | Phase 13.10 extended |
| Human review triggers | 32% (8/25) | 48% (12/25) | Phase 13.10 extended |
| Reviewer-ready rate | 68% (17/25) | 64% (16/25) | Phase 13.10 extended |
| Avg confidence | 0.825 | 0.644 | Phase 13.10 extended |
| Avg cited evidence | 2.0 | 1.8 | Phase 13.10 extended |
| Avg unsupported claims | 0.0 | 0.4 | Phase 13.10 extended |

**FakeLLMProvider (68% guard pass rate)**: Template-based deterministic output. Guard failures are 8 HIGH-severity cases lacking escalation acknowledgment — correct behavior.

**Real provider (deepseek-v4-pro, guard-aware prompt, 84% guard pass rate)**: Guard-aware structured prompt instructs LLM to include `[chunk_id]` citation markers inline. Dramatic improvement from Phase 13.9 baseline (4% guard pass, 12% citation valid). Remaining failures: 3 cases cite evidence but skip risk escalation acknowledgment; 1 case makes uncited substantive claim. 84% safe fallback rate is expected when prompt instructs conservative citing.

Source: `reports/eval/phase13_guard_aware_prompting_report.md` (Phase 13.10)

---

## 4. Provider Comparison

| Metric | FakeLLMProvider | Real Provider (deepseek-v4-pro, guard-aware) | Source |
|--------|-----------------|----------------------------------------------|--------|
| Cases | 25 | 25 | Phase 13.10 extended |
| Success count | 25 / 25 | 25 / 25 | Phase 13.10 extended |
| Avg confidence | 0.825 | 0.644 | Phase 13.10 extended |
| Human review triggers | 32% (8/25) | 48% (12/25) | Phase 13.10 extended |
| API errors | N/A | 0 | Phase 13.10 extended |
| Citation precision | 100% | 100% | Phase 13.10 extended |
| Citation validation pass | 100% (25/25) | 76% (19/25) | Phase 13.10 extended |
| Unsupported claim rate | 0% | 24% (6/25) | Phase 13.10 extended |
| Forbidden promise count | 0 | 1 | Phase 13.10 extended |
| Guard pass rate | 68% (17/25) | 84% (21/25) | Phase 13.10 extended |
| Safe fallback rate | 0% | 84% (21/25) | Phase 13.10 extended |
| Reviewer-ready rate | 68% (17/25) | 64% (16/25) | Phase 13.10 extended |
| Latency | N/A | not yet measured | — |
| Estimated cost | N/A | not yet measured | — |

**Source**: `reports/eval/phase13_guard_aware_prompting_summary.json` (Phase 13.10)
**Boundary**: Offline fixture-based comparison on 25 synthetic cases with mock evidence — not a benchmark. Guard-aware prompt instructs LLM to include `[chunk_id]` citation markers. Remaining guard failures are correct guard behavior (risk escalation not acknowledged, unsupported claims).

---

## 5. Human Review / Risk Control

| Metric | Value | Source |
|--------|-------|--------|
| Risk flag types | 8 (complaint, compensation, legal, privacy, account_security, policy_conflict, low_confidence, insufficient_evidence) | `src/ticketpilot/risk/rules.py` |
| Severity levels | 3 (LOW / MEDIUM / HIGH) | `src/ticketpilot/risk/assessor.py` |
| Intent classes | 8 | `src/ticketpilot/classification/rules.py` |
| Human review forced on | HIGH severity, unsupported claims, citation validation failure, guard failure | `src/ticketpilot/drafting/generator.py` |
| Human review trigger (Phase 12) | 8 / 25 cases (both providers) | `phase12_llm_provider_comparison_rows.json` |
| Human review trigger (Phase 13.10) | 48% (12/25 real provider) | `phase13_guard_aware_prompting_report.md` |
| Human review correctness | not yet measured | — |

### Phase 15 UI Feature

| Feature | Description | Source |
|---------|-------------|--------|
| Chat-style AI Copilot | Multi-turn conversation UI | `src/ticketpilot/chat/app.py` |
| Evidence Panel | Sidebar showing citation sources | `src/ticketpilot/chat/pages/evidence_panel.py` |
| Risk Escalation Notification | Prominent warning for high-risk tickets | `src/ticketpilot/chat/pages/` |
| Pipeline-to-Chat Adapter | Converts pipeline output to chat messages | `src/ticketpilot/chat/adapter.py` |
| In-chat Human Review | Review operations embedded in chat UI | `src/ticketpilot/chat/` |

**Note**: Phase 15 Chat UI is MVP-level. Feature completeness and UX polish are iterative.

---

## 6. Engineering Quality Gate

| Check | Result | Source |
|-------|--------|--------|
| Unit tests | 1069 passed | `scripts/run_quality_gate.sh` |
| Integration tests | 146 passed, 0 skipped | same |
| Coverage | 87% (>= 70% threshold) | same |
| Ruff linting | All checks passed | same |
| OpenSpec --all | 22 / 22 passed | `openspec validate --all` |
| Secret scan | Clean | same |
| Quality gate | PASSED | same |

**Note**: Phase 12C.2 restored strict quality gate with `TICKETPILOT_LLM_PROVIDER=fake` isolation.
Source: `docs/changelog.md` Phase 12C.2 entry.

---

## 7. Limitations and Boundary Wording

**Metrics that should not be overclaimed:**

- **This is offline evaluation.** All metrics are computed against 101 synthetic tickets and 106 synthetic knowledge records. Results do not generalize to production environments.

- **This is not a real-world benchmark.** No real customer data, no live traffic, no production system involvement.

- **Provider comparison uses synthetic/adapted cases.** The 25-case Phase 12 fixture set covers diverse scenarios but is not a representative sample of real customer service volume.

- **Fake provider validates workflow mechanics, not real draft quality.** FakeLLMProvider is template-based and deterministic — it tests whether the pipeline handles inputs correctly, not whether generated text is semantically appropriate.

- **Real provider comparison is local offline fixture-based only.** The deepseek-v4-pro comparison was run on a fixed synthetic case set with mock evidence. It does not reflect live API performance.

- **Doc-ID Recall@10 = 91.9% is a retrieval metric.** It measures whether the right chunk was retrieved, not whether the final reply was correct or safe.

- **Human review triggers are rule-based.** 8/25 cases triggering human review reflects the current rule configuration on a specific fixture set — not a universal rate.

- **Engineering quality gate measures code quality, not product quality.** Passing tests and coverage thresholds do not imply the system is production-ready.

---

## Not-Yet-Measured Metrics

The following metrics are not yet available from repo reports:

| Metric | Status | Shortest path to obtain |
|--------|--------|------------------------|
| Guard pass rate for real provider | **Now measured**: 84% (21/25, guard-aware) | Done — Phase 13.10 |
| Real provider latency | Not yet measured | Time Phase 12 comparison runner API calls |
| Real provider estimated cost | Not yet measured | Multiply API call count by per-token pricing |
| Human review trigger correctness (real provider) | Not yet measured | Label Phase 12 fixtures with expected human review |
| Reviewer-ready rate (per-provider) | **Fake=68%, Real=64%** | Computed from Phase 13.10: guard_passed + unsupported_claims=0 + citation_valid |