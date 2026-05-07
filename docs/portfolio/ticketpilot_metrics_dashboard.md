# TicketPilot Metrics Dashboard

**Scope**: Local demo / portfolio prototype — NOT a production benchmark
**Last updated**: 2026-05-07

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
**Boundary**: Offline evaluation on 101 synthetic tickets — not a production benchmark.

---

## 3. Draft Generation Evaluation

| Metric | Value | Source |
|--------|-------|--------|
| Citation precision (Phase 12 extended) | 100% (25/25 cases) | `phase12_llm_provider_comparison_summary.json` |
| Evidence coverage avg (Phase 12) | 100% | same |
| Unsupported claim rate (Phase 12) | 0% (0/25) | same |
| Forbidden promise rate (Phase 12) | 0% (0/25) | same |
| Safe fallback rate (Phase 12) | 0% (0/25) | same |
| Human-review trigger correctness (Phase 12) | 100% (25/25) | same |
| Citation validation pass rate (Phase 12) | 100% (25/25) | same |
| Claim guard pass rate (Phase 12) | 0% (0/25) | same — all FakeLLMProvider drafts fail guard (uncited claims) |
| Average confidence (Phase 12) | 0.825 | same |

**Note**: Phase 13 extended the Phase 12 comparison runner to produce `DraftEvaluationRow` objects
with citation validation and claim guard results from `DraftGenerationResult`.
FakeLLMProvider produces correct citations but all drafts fail claim guard — this reflects
the template-based provider's output characteristics on the fixture set.
Source: `reports/eval/phase12_llm_provider_comparison_summary.json` (Phase 13 extended output)

---

## 4. Provider Comparison

| Metric | FakeLLMProvider | OpenAICompatibleProvider (deepseek-v4-pro) | Source |
|--------|-----------------|---------------------------------------------|--------|
| Cases | 25 | 25 | `phase12_llm_provider_comparison_summary.json` |
| Success count | 25 / 25 | 25 / 25 | same |
| Avg confidence | 0.85 | 0.70 | same |
| Human review triggers | 8 | 8 | same |
| API errors | N/A | 0 | same |
| Citation precision | 100% | 100% | Phase 13 extended (25/25 cases each) |
| Unsupported claim rate | 0% | 0% | Phase 13 extended |
| Forbidden promise count | 0 | 0 | Phase 13 extended |
| Guard pass rate | 0% | — | Phase 13 extended (real provider not run) |
| Latency | N/A | not yet measured | — |
| Estimated cost | N/A | not yet measured | — |

**Source**: `reports/eval/phase12_llm_provider_comparison_summary.json` (Phase 13 extended output)
**Boundary**: Offline fixture-based comparison on 25 synthetic cases — not a benchmark.

---

## 5. Human Review / Risk Control

| Metric | Value | Source |
|--------|-------|--------|
| Risk flag types | 8 (complaint, compensation, legal, privacy, account_security, policy_conflict, low_confidence, insufficient_evidence) | `src/ticketpilot/risk/rules.py` |
| Severity levels | 3 (LOW / MEDIUM / HIGH) | `src/ticketpilot/risk/assessor.py` |
| Intent classes | 8 | `src/ticketpilot/classification/rules.py` |
| Human review forced on | HIGH severity, unsupported claims, citation validation failure, guard failure | `src/ticketpilot/drafting/generator.py` |
| Human review trigger (Phase 12) | 8 / 25 cases (both providers) | `phase12_llm_provider_comparison_rows.json` |
| Human review correctness | not yet measured | — |

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
| Guard pass rate for real provider | Not yet measured | Run Phase 13 extended runner with real provider |
| Real provider latency | Not yet measured | Time Phase 12 comparison runner API calls |
| Real provider estimated cost | Not yet measured | Multiply API call count by per-token pricing |
| Human review trigger correctness (real provider) | Not yet measured | Label Phase 12 fixtures with expected human review |
| Reviewer-ready rate (per-provider) | Not yet measured | Compute from Phase 13 extended rows: citation_valid + guard_passed + unsupported_claims=0 |
