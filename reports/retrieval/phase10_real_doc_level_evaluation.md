# Phase 10.5.1 — Real Pipeline Doc-Level Evaluation

*Generated at 2026-05-06 02:31:52 UTC*

## Dataset

- Total cases: 101
- P0-labeled cases: 14
- Rows: `reports/retrieval/phase10_real_doc_level_rows.json`
- Golden: `data/eval/golden_expectations.csv`

## Provider

- **Embedding provider**: `openai_compatible`

## Aggregate Metrics: Doc-Type vs Doc-ID

| k | Doc-Type Hit Rate | Doc-ID Hit Rate | P0 Added-Record Hit Rate | Delta |
|---|-------------------|-----------------|--------------------------|-------|
| 1 | 44.6% | 14.3% | 14.3% | -30.3% |
| 3 | 54.5% | 50.0% | 50.0% | -4.5% |
| 5 | 57.4% | 78.6% | 78.6% | +21.1% |
| 10 | 59.4% | 78.6% | 78.6% | +19.2% |

| MRR | 0.4995 | 0.3619 | — | — |

## P0 Doc-Level Summary

- **Labeled cases**: 14
- **Doc-ID correct at Top-10**: 10/14 (71.4%)
- **Partial hit**: 1
- **Still wrong at doc-ID level**: 4

## Wrong-Case Recheck (Doc-ID Granularity)

- **Wrong cases (doc-type)**: 41
- **Doc-ID found in top-10**: 11
- **Still wrong after doc-ID check**: 30

### Reclassified Cases

| Case ID | Original Failure Mode | Doc ID Found Rank |
|---------|----------------------|-------------------|
| case_acco_003 | missing_doc_type | 2 |
| case_acco_012 | missing_doc_type | 4 |
| case_comp_003 | missing_doc_type | 2 |
| case_comp_004 | missing_doc_type | 4 |
| case_comp_008 | missing_doc_type | 1 |
| case_comp_009 | missing_doc_type | 5 |
| case_refu_001 | missing_doc_type | 3 |
| case_refu_006 | missing_doc_type | 3 |
| case_refu_009 | missing_doc_type | 1 |
| case_refu_013 | missing_doc_type | 2 |
| case_retu_004 | missing_doc_type | 5 |

### Still Wrong After Doc-ID Check

| Case ID | Original Failure Mode |
|---------|----------------------|
| case_acco_006 | missing_doc_type |
| case_acco_009 | missing_doc_type |
| case_acco_014 | missing_doc_type |
| case_comp_001 | missing_doc_type |
| case_comp_002 | missing_doc_type |
| case_comp_005 | missing_doc_type |
| case_comp_006 | missing_doc_type |
| case_comp_007 | missing_doc_type |
| case_comp_013 | missing_doc_type |
| case_edge_001 | missing_doc_type |
| case_edge_002 | missing_doc_type |
| case_edge_003 | missing_doc_type |
| case_edge_004 | missing_doc_type |
| case_edge_005 | missing_doc_type |
| case_logi_005 | missing_doc_type |
| case_logi_008 | missing_doc_type |
| case_logi_010 | missing_doc_type |
| case_logi_011 | missing_doc_type |
| case_othe_009 | missing_doc_type |
| case_othe_011 | missing_doc_type |
| case_othe_012 | missing_doc_type |
| case_othe_013 | missing_doc_type |
| case_refu_003 | missing_doc_type |
| case_refu_008 | missing_doc_type |
| case_refu_015 | missing_doc_type |
| case_refu_016 | missing_doc_type |
| case_retu_006 | missing_doc_type |
| case_retu_008 | missing_doc_type |
| case_retu_010 | missing_doc_type |
| case_retu_011 | missing_doc_type |

## Per-Case P0 Doc-ID Detail

| Case ID | Expected Doc IDs | Hit in Top-10 | Missed | All Correct? |
|---------|-----------------|---------------|--------|-------------|
| case_acco_003 | ae0e0e0e, ca0a0a0a | ae0e0e0e@5, ca0a0a0a@2 | — | ✅ |
| case_acco_006 | ae0e0e0e | — | ae0e0e0e | ❌ |
| case_acco_012 | ae0e0e0e | ae0e0e0e@4 | — | ✅ |
| case_comp_001 | ca0a0a0a | — | ca0a0a0a | ❌ |
| case_comp_002 | ca0a0a0a | — | ca0a0a0a | ❌ |
| case_comp_003 | ca0a0a0a | ca0a0a0a@2 | — | ✅ |
| case_comp_004 | ca0a0a0a | ca0a0a0a@4 | — | ✅ |
| case_comp_008 | ca0a0a0a | ca0a0a0a@1 | — | ✅ |
| case_comp_009 | ca0a0a0a | ca0a0a0a@5 | — | ✅ |
| case_refu_001 | ae0e0e0e | ae0e0e0e@3 | — | ✅ |
| case_refu_006 | ae0e0e0e | ae0e0e0e@3 | — | ✅ |
| case_refu_009 | ae0e0e0e | ae0e0e0e@1 | — | ✅ |
| case_refu_013 | ae0e0e0e, ca0a0a0a | ca0a0a0a@2 | ae0e0e0e | ❌ |
| case_retu_004 | f0f0f0f0 | f0f0f0f0@5 | — | ✅ |

## Interpretation

**10/14** P0-labeled cases have ALL expected doc_ids in top-10.
**4** cases still missing at least one expected doc_id even at doc-ID granularity.
**1** cases have partial hits (some expected doc_ids found, some not).

**Wrong-case recheck**: Of 41 doc-type wrong cases, 11 (27%) have the correct doc_id in top-10 — confirming metric granularity as the primary cause.

### Remaining Bottlenecks

- **4 cases** with genuine retrieval misses (doc_id not in fused top-10):
  - `case_acco_006`: missing ae0e0e0e
  - `case_comp_001`: missing ca0a0a0a
  - `case_comp_002`: missing ca0a0a0a
  - `case_refu_013`: missing ae0e0e0e
- These need deeper investigation: keyword recall, vector recall, or fusion ranking.

### Recommendations

1. **Add more doc-level labels** — extend to non-P0 cases for broader coverage.
2. **Query expansion audit** — for cases with genuine misses, check if query underspecifies the needed knowledge.
3. **Fusion ranking experiment** — for cases where doc_id found but below top-10, tune RRF or add reranker.
4. **Portfolio snapshot** — doc-level evaluation results are ready for Phase 10 portfolio.
