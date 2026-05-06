# Phase 10.7 — Full-Dataset Doc-Level Evaluation

*Generated at 2026-05-06 UTC*
*Part of Phase 10: Hybrid Retrieval Ranking Diagnosis*

> **Boundary statement:**
> - Mock-mode evaluation. All doc_id-level metrics use synthetic retrieval (not real pipeline).
> - Real doc_id evaluation requires `export` mode pipeline run with real provider.
> - No retrieval algorithm, RRF, embedding provider, or knowledge base changes.
> - All 101 eval tickets and 73 knowledge records are synthetic.

---

## 1. Label Coverage

| Metric | Value |
|---|---|
| Total eval cases | 101 |
| Cases with `expected_relevant_doc_ids` | **86** (85.1%) |
| Cases sent to manual review | 15 |
| Unlabeled (manual review) | 15 |

### Label Coverage by Domain

| Domain | Total | Labeled | Unlabeled | Manual Review Reasons |
|---|---|---|---|---|
| refund | 16 | 16 | 0 | — |
| return_exchange | 11 | 11 | 0 | — |
| account_issue | 15 | 15 | 0 | — |
| technical | 9 | 9 | 0 | — |
| product_consulting | 8 | 7 | 1 (case_prod_003) | Membership benefits not in knowledge seed |
| logistics | 11 | 11 | 0 | — |
| complaint | 13 | 13 | 0 | — |
| other (invoice/billing) | 13 | 8 | 5 | Job inquiries, store locations, points, WeChat groups, suggestions |
| edge (non-semantic) | 5 | 0 | 5 | Single-char, special chars, symbols only |

---

## 2. Mock-Mode Metrics

### Doc-Type Hit Rate

| k | Hit Rate | Wrong Cases |
|---|---|---|
| 1 | 96.0% | 4 |
| 3 | 96.0% | 4 |
| 5 | 96.0% | 4 |
| 10 | 96.0% | 4 |

### Doc-ID Hit Rate (Mock Mode)

| k | Hit Rate |
|---|---|
| 1 | 0.0% |
| 3 | 0.0% |
| 5 | 0.0% |
| 10 | 0.0% |

### MRR

| Metric | Value |
|---|---|
| MRR (doc_type) | 0.9604 |
| MRR (doc_id) | 0.0000 |

### Wrong Cases (Doc-Type)

All 4 wrong cases are edge cases with empty `expected_evidence_doc_types`:

| Case ID | Issue | Expected Doc Types |
|---|---|---|
| case_edge_001 | Single character "退" | (empty) |
| case_edge_003 | Special characters only | (empty) |
| case_edge_004 | Chinese with special chars | (empty) |
| case_edge_005 | Numbers and symbols only | (empty) |

---

## 3. Interpretation

### Key Finding: Label Coverage Is Now Sufficient for Full-Dataset Doc-Level Analysis

The primary goal of Phase 10.7 was achieved: **86/101 cases (85.1%) now have doc-level golden labels**. This enables:

1. **Full-dataset wrong-case reclassification**: The 14 P0 cases from Phase 10.5.1 showed 71.4% doc_id-correct. With 86 labeled cases, the same analysis can run across the entire eval set — but requires real pipeline export.
2. **Precise bottleneck measurement**: Each case's expected doc_ids are explicitly defined, so we can measure exactly which knowledge records are (or aren't) retrieved.
3. **Metric granularity thesis**: The Phase 10 thesis — that most "wrong" cases are metric granularity problems — can now be tested across all domains, not just P0.

### Doc-Type Metrics: 96% Baseline

The mock-mode doc_type hit rate is 96.0% — only 4 edge cases fail because they have empty expected_doc_types. This is expected behavior: the mock generator reliably produces docs of any requested type.

### Doc-ID Metrics: 0% in Mock Mode

All doc_id metrics show 0% in mock mode because the mock generator uses synthetic IDs (`doc_faq_0001` format) that never match the real UUIDs in `expected_relevant_doc_ids`. This is **expected and documented behavior** — doc_id metrics require real pipeline export.

### Manual Review Cases: 15

The 15 unlabeled cases fall into 3 categories:

1. **Knowledge gaps (4)**: job inquiries, store locations, points balance, WeChat groups — no FAQ/Policy/Coverage exists in current seed
2. **Edge cases (5)**: non-semantic content cannot be mapped to any knowledge record
3. **Ambiguous/low-confidence (6)**: membership benefits, packaging suggestions, multi-issue tickets, weak POLICY-only matches

These cases do not affect the doc_type metric (they have no expected_doc_types) and are skipped in doc_id evaluation.

---

## 4. Comparison with Phase 10.5.1 (P0 Real Pipeline)

| Metric | Phase 10.5.1 (14 P0, Real) | Phase 10.7 (86 Labeled, Mock) |
|---|---|---|
| Labeled cases | 14 | 86 |
| doc_type hit rate @10 | Not measured (subset) | 96.0% |
| doc_id Recall@10 | **78.6%** | 0.0% (mock limitation) |
| Wrong cases reclassified | 11/41 (26.8%) | N/A (mock mode) |
| Remaining true misses | 4 | N/A (mock mode) |

**Key insight**: The 78.6% doc_id Recall@10 from Phase 10.5.1 was measured on 14 P0 cases with real provider. With 86 cases now labeled, the same analysis on the full dataset would give a statistically robust picture — but requires real pipeline export.

---

## 5. Remaining Issues

### By Category

| Category | Count | Details |
|---|---|---|
| **Knowledge gap** | 4 | No seed records for job/HR, store locations, points, WeChat groups |
| **Label ambiguity** | 4 | Membership, packaging suggestion, multi-issue edge, reschedule delivery |
| **Edge cases** | 5 | Non-semantic content (single char, special chars, symbols) |
| **Weak match** | 2 | Only POLICY available for tech_005 (slow website) and tech_006 (address selection) |

### Impact on Wrong-Case Reclassification

The 41 doc-type wrong cases from Phase 9/10 cannot be re-evaluated without real pipeline export. However, with 86 cases now labeled:

- **14 P0 cases already evaluated**: 10/14 doc_id-correct (71.4%), 11/41 wrong cases reclassified (partial)
- **72 newly labeled cases**: Ready for real pipeline evaluation when export is run
- **15 unlabeled cases**: Will remain unclassified — they have no expected doc_ids

---

## 6. Recommendations

### Should Phase 10 Be Archived?

**Yes, after one more step**: Run real pipeline export on all 86 labeled cases to get the full-dataset doc_id metrics. This is a one-command operation (pipeline export mode) that would validate whether the metric granularity thesis holds across all domains — not just P0.

### Next Steps (Updated Priority)

| Priority | Action | Impact | Effort | Prerequisites |
|---|---|---|---|---|
| **P0 (done)** | ✅ Doc-level labels expanded to 86/101 cases | High | Medium | — |
| **P0.5** | **Run real pipeline export on 86 labeled cases** | High | Low (one command) | Labels in place |
| **P1** | Query expansion audit for 4 true misses | Medium | Low | Real export confirms misses |
| **P2** | Fusion ranking experiment | Low-Med | Medium | After labels + query audit |
| **P3** | Reranker proposal | Uncertain | High | Future |
| **Defer** | Add knowledge seed for 4 gap topics | Low | Medium | Not blocking retrieval eval |

### What Phase 10.7 Confirms

1. **Label coverage is no longer the bottleneck** — 86/101 cases labeled
2. **Doc-level evaluation is now possible across all domains** — requires real pipeline
3. **15 cases cannot be labeled** — knowledge gaps and edge cases. Acceptable.
4. **Phase 10 metric granularity thesis stands** — but needs full-dataset real export for final confirmation
5. **The next bottleneck is real pipeline evaluation**, not labeling

---

## 7. Metrics Summary Table

| Metric | Value | Notes |
|---|---|---|
| `labeled_case_count` | 86 | Out of 101 total |
| `unlabeled_case_count` | 15 | All in manual review categories |
| `doc_id_recall_at_1` | 0.0% | Mock limitation — requires real pipeline |
| `doc_id_recall_at_3` | 0.0% | Mock limitation — requires real pipeline |
| `doc_id_recall_at_5` | 0.0% | Mock limitation — requires real pipeline |
| `doc_id_recall_at_10` | 0.0% | Mock limitation — requires real pipeline |
| `doc_id_mrr` | 0.0% | Mock limitation — requires real pipeline |
| `doc_type_hit_rate_at_10` | 96.0% | Only 4 edge cases fail |
| `doc_id_found_among_doc_type_wrong` | 0/4 | All 4 are edge cases with no expected ids |
| `doc_type_wrong_reclassified_count` | 0 | Requires real pipeline for meaningful recheck |
| `remaining_true_miss_count` | 4 (Phase 10.5.1) | Requires real pipeline for full dataset |
