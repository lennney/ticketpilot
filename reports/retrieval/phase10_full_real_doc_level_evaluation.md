# Phase 10.7.5 — Real Pipeline Doc-Level Evaluation

*Generated at 2026-05-06 04:19:06 UTC*
*Mode: full*

## Dataset

- Total cases: 101
- Labeled cases: 86
- Unlabeled cases: 15
- Rows: `reports/retrieval/phase10_full_real_doc_level_rows.json`
- Golden: `data/eval/golden_expectations.csv`

## Provider

- **Embedding provider**: `openai_compatible`

## Aggregate Metrics: Doc-Type vs Doc-ID

| k | Doc-Type Hit Rate | Doc-ID Hit Rate | Delta |
|---|-------------------|-----------------|-------|
| 1 | 44.6% | 30.2% | -14.3% |
| 3 | 54.5% | 61.6% | +7.2% |
| 5 | 57.4% | 79.1% | +21.6% |
| 10 | 59.4% | 91.9% | +32.5% |

| MRR | 0.4995 | 0.4881 | — |

## Doc-ID Level Summary

- **Labeled cases**: 86
- **Unlabeled cases**: 15
- **Doc-ID correct at Top-10**: 47/86 (54.7%)
- **Partial hit**: 32
- **Still wrong at doc-ID level**: 39

## Wrong-Case Recheck (Doc-ID Granularity)

- **Wrong cases (doc-type)**: 41
- **Doc-ID found in top-10**: 32
- **Still wrong after doc-ID check**: 9

### Reclassified Cases

| Case ID | Original Failure Mode | Doc ID Found Rank |
|---------|----------------------|-------------------|
| case_acco_003 | missing_doc_type | 2 |
| case_acco_009 | missing_doc_type | 6 |
| case_acco_012 | missing_doc_type | 4 |
| case_acco_014 | missing_doc_type | 8 |
| case_comp_003 | missing_doc_type | 2 |
| case_comp_004 | missing_doc_type | 4 |
| case_comp_005 | missing_doc_type | 1 |
| case_comp_006 | missing_doc_type | 1 |
| case_comp_007 | missing_doc_type | 6 |
| case_comp_008 | missing_doc_type | 1 |
| case_comp_009 | missing_doc_type | 5 |
| case_comp_013 | missing_doc_type | 2 |
| case_logi_005 | missing_doc_type | 5 |
| case_logi_008 | missing_doc_type | 3 |
| case_logi_011 | missing_doc_type | 4 |
| case_othe_009 | missing_doc_type | 3 |
| case_othe_011 | missing_doc_type | 3 |
| case_othe_012 | missing_doc_type | 3 |
| case_othe_013 | missing_doc_type | 1 |
| case_refu_001 | missing_doc_type | 3 |
| case_refu_003 | missing_doc_type | 1 |
| case_refu_006 | missing_doc_type | 3 |
| case_refu_008 | missing_doc_type | 3 |
| case_refu_009 | missing_doc_type | 1 |
| case_refu_013 | missing_doc_type | 2 |
| case_refu_015 | missing_doc_type | 2 |
| case_refu_016 | missing_doc_type | 2 |
| case_retu_004 | missing_doc_type | 5 |
| case_retu_006 | missing_doc_type | 1 |
| case_retu_008 | missing_doc_type | 1 |
| case_retu_010 | missing_doc_type | 5 |
| case_retu_011 | missing_doc_type | 7 |

### Still Wrong After Doc-ID Check

| Case ID | Original Failure Mode |
|---------|----------------------|
| case_acco_006 | missing_doc_type |
| case_comp_001 | missing_doc_type |
| case_comp_002 | missing_doc_type |
| case_edge_001 | missing_doc_type |
| case_edge_002 | missing_doc_type |
| case_edge_003 | missing_doc_type |
| case_edge_004 | missing_doc_type |
| case_edge_005 | missing_doc_type |
| case_logi_010 | missing_doc_type |

## Per-Case Doc-ID Detail

| Case ID | Expected Doc IDs | Hit in Top-10 | Missed | All Correct? |
|---------|-----------------|---------------|--------|-------------|
| case_acco_001 | 44444444, a5555555, b4444444 | 44444444@2, a5555555@3, b4444444@8 | — | ✅ |
| case_acco_002 | 55555555, a5555555, eeeeeeee | 55555555@5, a5555555@7, eeeeeeee@9 | — | ✅ |
| case_acco_003 | ae0e0e0e, ca0a0a0a | ae0e0e0e@5, ca0a0a0a@2 | — | ✅ |
| case_acco_004 | 44444444, a5555555, ad0d0d0d, c5555555 | c5555555@7 | 44444444, a5555555, ad0d0d0d | ⚠️ partial |
| case_acco_005 | 55555555, b5555555, eeeeeeee | 55555555@1, b5555555@2, eeeeeeee@6 | — | ✅ |
| case_acco_006 | ae0e0e0e | — | ae0e0e0e | ❌ |
| case_acco_007 | 55555555, a5555555 | 55555555@3, a5555555@8 | — | ✅ |
| case_acco_008 | ad0d0d0d, c5555555, eeeeeeee | ad0d0d0d@7, c5555555@1, eeeeeeee@2 | — | ✅ |
| case_acco_009 | a6666666 | a6666666@6 | — | ✅ |
| case_acco_010 | ae0e0e0e, ffffffff | ae0e0e0e@9, ffffffff@1 | — | ✅ |
| case_acco_011 | a5555555, eeeeeeee | a5555555@10, eeeeeeee@1 | — | ✅ |
| case_acco_012 | ae0e0e0e | ae0e0e0e@4 | — | ✅ |
| case_acco_013 | eeeeeeee, ffffffff | eeeeeeee@4, ffffffff@1 | — | ✅ |
| case_acco_014 | ad0d0d0d, ae0e0e0e, ca0a0a0a, eeeeeeee | eeeeeeee@8 | ad0d0d0d, ae0e0e0e, ca0a0a0a | ⚠️ partial |
| case_acco_015 | 44444444, a5555555, ad0d0d0d | — | 44444444, a5555555, ad0d0d0d | ❌ |
| case_comp_001 | ca0a0a0a | — | ca0a0a0a | ❌ |
| case_comp_002 | ca0a0a0a | — | ca0a0a0a | ❌ |
| case_comp_003 | ca0a0a0a | ca0a0a0a@2 | — | ✅ |
| case_comp_004 | ca0a0a0a | ca0a0a0a@4 | — | ✅ |
| case_comp_005 | ad0d0d0d, ae0e0e0e, c4444444, ca0a0a0a | ad0d0d0d@3, ae0e0e0e@6, c4444444@1, ca0a0a0a@4 | — | ✅ |
| case_comp_006 | a9999999, ad0d0d0d, c3333333 | a9999999@6, ad0d0d0d@5, c3333333@1 | — | ✅ |
| case_comp_007 | a9999999, b1111111, eeeeeeee | b1111111@8, eeeeeeee@6 | a9999999 | ⚠️ partial |
| case_comp_008 | ca0a0a0a | ca0a0a0a@1 | — | ✅ |
| case_comp_009 | ca0a0a0a | ca0a0a0a@5 | — | ✅ |
| case_comp_010 | a9999999, aaaaaaaa | a9999999@7 | aaaaaaaa | ⚠️ partial |
| case_comp_011 | a9999999, aaaaaaaa | aaaaaaaa@5 | a9999999 | ⚠️ partial |
| case_comp_012 | a9999999, eeeeeeee | a9999999@6 | eeeeeeee | ⚠️ partial |
| case_comp_013 | ad0d0d0d, ae0e0e0e, c4444444, ca0a0a0a | ad0d0d0d@4, ae0e0e0e@7, c4444444@2, ca0a0a0a@3 | — | ✅ |
| case_logi_001 | a7777777, c8888888, dddddddd | a7777777@7, c8888888@4, dddddddd@2 | — | ✅ |
| case_logi_002 | 99999999, a8888888, b2222222 | 99999999@4, b2222222@3 | a8888888 | ⚠️ partial |
| case_logi_003 | 88888888, a7777777 | 88888888@3 | a7777777 | ⚠️ partial |
| case_logi_005 | 99999999, a8888888, b8888888 | 99999999@8, a8888888@9, b8888888@5 | — | ✅ |
| case_logi_006 | a7777777, dddddddd | a7777777@7, dddddddd@1 | — | ✅ |
| case_logi_007 | a7777777, ffffffff | a7777777@2, ffffffff@1 | — | ✅ |
| case_logi_008 | ae0e0e0e, c8888888, dddddddd | ae0e0e0e@6, c8888888@7, dddddddd@3 | — | ✅ |
| case_logi_010 | 99999999, a8888888, b9999999 | — | 99999999, a8888888, b9999999 | ❌ |
| case_logi_011 | a8888888, ae0e0e0e, b8888888 | b8888888@4 | a8888888, ae0e0e0e | ⚠️ partial |
| case_othe_002 | ad0d0d0d, c7777777, dddddddd | ad0d0d0d@4, c7777777@5, dddddddd@3 | — | ✅ |
| case_othe_003 | ad0d0d0d, dddddddd | ad0d0d0d@4, dddddddd@3 | — | ✅ |
| case_othe_006 | ca0a0a0a, ffffffff | ca0a0a0a@4, ffffffff@3 | — | ✅ |
| case_othe_009 | ad0d0d0d, c6666666, dddddddd | ad0d0d0d@6, c6666666@3, dddddddd@4 | — | ✅ |
| case_othe_010 | ad0d0d0d, b7777777, eeeeeeee | ad0d0d0d@7, b7777777@3, eeeeeeee@1 | — | ✅ |
| case_othe_011 | ad0d0d0d, c7777777, dddddddd | ad0d0d0d@4, c7777777@6, dddddddd@3 | — | ✅ |
| case_othe_012 | ad0d0d0d, c7777777, dddddddd | ad0d0d0d@3, c7777777@5, dddddddd@4 | — | ✅ |
| case_othe_013 | ad0d0d0d, c7777777, dddddddd | ad0d0d0d@2, c7777777@1, dddddddd@3 | — | ✅ |
| case_prod_001 | abbbbbbb, ffffffff | ffffffff@1 | abbbbbbb | ⚠️ partial |
| case_prod_002 | ffffffff | ffffffff@1 | — | ✅ |
| case_prod_004 | abbbbbbb, ffffffff | ffffffff@2 | abbbbbbb | ⚠️ partial |
| case_prod_005 | ffffffff | ffffffff@1 | — | ✅ |
| case_prod_006 | abbbbbbb, ffffffff | abbbbbbb@2, ffffffff@3 | — | ✅ |
| case_prod_007 | ffffffff | ffffffff@1 | — | ✅ |
| case_prod_008 | abbbbbbb, ffffffff | abbbbbbb@4 | ffffffff | ⚠️ partial |
| case_refu_001 | ae0e0e0e | ae0e0e0e@3 | — | ✅ |
| case_refu_002 | 11111111, 22222222, a1111111, ad0d0d0d | 22222222@5, a1111111@2 | 11111111, ad0d0d0d | ⚠️ partial |
| case_refu_003 | a3333333, ae0e0e0e, dddddddd | dddddddd@1 | a3333333, ae0e0e0e | ⚠️ partial |
| case_refu_004 | 11111111, a1111111, ffffffff | 11111111@9, ffffffff@5 | a1111111 | ⚠️ partial |
| case_refu_005 | 22222222, ad0d0d0d, ae0e0e0e, dddddddd | 22222222@4, ad0d0d0d@1, ae0e0e0e@5 | dddddddd | ⚠️ partial |
| case_refu_006 | ae0e0e0e | ae0e0e0e@3 | — | ✅ |
| case_refu_007 | 11111111, a1111111, ffffffff | ffffffff@6 | 11111111, a1111111 | ⚠️ partial |
| case_refu_008 | a3333333, ae0e0e0e, cccccccc | ae0e0e0e@3 | a3333333, cccccccc | ⚠️ partial |
| case_refu_009 | ae0e0e0e | ae0e0e0e@1 | — | ✅ |
| case_refu_010 | a3333333, ae0e0e0e, cccccccc | a3333333@10, cccccccc@8 | ae0e0e0e | ⚠️ partial |
| case_refu_011 | 11111111, a1111111, accccccc | a1111111@2 | 11111111, accccccc | ⚠️ partial |
| case_refu_012 | a1111111, ae0e0e0e, ca0a0a0a, dddddddd, eeeeeeee | — | a1111111, ae0e0e0e, ca0a0a0a, dddddddd, eeeeeeee | ❌ |
| case_refu_013 | ae0e0e0e, ca0a0a0a | ca0a0a0a@2 | ae0e0e0e | ⚠️ partial |
| case_refu_014 | a1111111, ffffffff | ffffffff@1 | a1111111 | ⚠️ partial |
| case_refu_015 | 22222222, ad0d0d0d, ae0e0e0e, c3333333, dddddddd | 22222222@7, ad0d0d0d@8, ae0e0e0e@4, c3333333@2 | dddddddd | ⚠️ partial |
| case_refu_016 | ae0e0e0e, ca0a0a0a, ffffffff | ae0e0e0e@4, ca0a0a0a@2 | ffffffff | ⚠️ partial |
| case_retu_001 | 33333333, a4444444, dddddddd | 33333333@4, a4444444@5, dddddddd@7 | — | ✅ |
| case_retu_002 | 33333333, a3333333, a4444444 | 33333333@4, a4444444@10 | a3333333 | ⚠️ partial |
| case_retu_003 | a4444444, b3333333, dddddddd | a4444444@8, b3333333@6, dddddddd@5 | — | ✅ |
| case_retu_004 | f0f0f0f0 | f0f0f0f0@5 | — | ✅ |
| case_retu_005 | a3333333, bcccccc1, cccccccc | a3333333@9 | bcccccc1, cccccccc | ⚠️ partial |
| case_retu_006 | a4444444, bcccccc1, ffffffff | a4444444@4, ffffffff@1 | bcccccc1 | ⚠️ partial |
| case_retu_007 | 33333333, a4444444 | — | 33333333, a4444444 | ❌ |
| case_retu_008 | a4444444, ae0e0e0e, dddddddd | a4444444@4, ae0e0e0e@5, dddddddd@1 | — | ✅ |
| case_retu_009 | 33333333, a4444444, ffffffff | 33333333@5, a4444444@4, ffffffff@6 | — | ✅ |
| case_retu_010 | a3333333, ad0d0d0d, cccccccc | a3333333@8, cccccccc@5 | ad0d0d0d | ⚠️ partial |
| case_retu_011 | a9999999, b3333333, eeeeeeee | b3333333@7 | a9999999, eeeeeeee | ⚠️ partial |
| case_tech_001 | 66666666, aaaaaaaa, b6666666 | 66666666@3, aaaaaaaa@10, b6666666@4 | — | ✅ |
| case_tech_002 | aaaaaaaa, bbbbbbbb | bbbbbbbb@3 | aaaaaaaa | ⚠️ partial |
| case_tech_003 | ad0d0d0d, ad0d0d0d, b7777777, eeeeeeee | b7777777@3, eeeeeeee@1 | ad0d0d0d, ad0d0d0d | ⚠️ partial |
| case_tech_004 | aaaaaaaa, f0f0f0f0 | f0f0f0f0@1 | aaaaaaaa | ⚠️ partial |
| case_tech_007 | 66666666, ca0a0a0a | 66666666@3, ca0a0a0a@1 | — | ✅ |
| case_tech_008 | ad0d0d0d, b7777777, eeeeeeee | ad0d0d0d@5, b7777777@3, eeeeeeee@1 | — | ✅ |
| case_tech_009 | aaaaaaaa, dddddddd | aaaaaaaa@8, dddddddd@6 | — | ✅ |

## Interpretation

**47/86** labeled cases have ALL expected doc_ids in top-10.
**39** cases still missing at least one expected doc_id at doc-ID granularity.
**32** cases have partial hits (some expected doc_ids found, some not).

**Wrong-case recheck**: Of 41 doc-type wrong cases, 32 (78%) have the correct doc_id in top-10 — confirming metric granularity as the primary cause.

**✅ Thesis confirmed**: The majority of wrong cases are metric granularity problems.

### Remaining Bottlenecks

- **39 cases** with genuine retrieval misses (doc_id not in fused top-10):
  - `case_acco_004`: missing 44444444, a5555555, ad0d0d0d (partial: some found)
  - `case_acco_006`: missing ae0e0e0e
  - `case_acco_014`: missing ad0d0d0d, ae0e0e0e, ca0a0a0a (partial: some found)
  - `case_acco_015`: missing 44444444, a5555555, ad0d0d0d
  - `case_comp_001`: missing ca0a0a0a
  - `case_comp_002`: missing ca0a0a0a
  - `case_comp_007`: missing a9999999 (partial: some found)
  - `case_comp_010`: missing aaaaaaaa (partial: some found)
  - `case_comp_011`: missing a9999999 (partial: some found)
  - `case_comp_012`: missing eeeeeeee (partial: some found)
  - `case_logi_002`: missing a8888888 (partial: some found)
  - `case_logi_003`: missing a7777777 (partial: some found)
  - `case_logi_010`: missing 99999999, a8888888, b9999999
  - `case_logi_011`: missing a8888888, ae0e0e0e (partial: some found)
  - `case_prod_001`: missing abbbbbbb (partial: some found)
  - `case_prod_004`: missing abbbbbbb (partial: some found)
  - `case_prod_008`: missing ffffffff (partial: some found)
  - `case_refu_002`: missing 11111111, ad0d0d0d (partial: some found)
  - `case_refu_003`: missing a3333333, ae0e0e0e (partial: some found)
  - `case_refu_004`: missing a1111111 (partial: some found)
  - `case_refu_005`: missing dddddddd (partial: some found)
  - `case_refu_007`: missing 11111111, a1111111 (partial: some found)
  - `case_refu_008`: missing a3333333, cccccccc (partial: some found)
  - `case_refu_010`: missing ae0e0e0e (partial: some found)
  - `case_refu_011`: missing 11111111, accccccc (partial: some found)
  - `case_refu_012`: missing a1111111, ae0e0e0e, ca0a0a0a, dddddddd, eeeeeeee
  - `case_refu_013`: missing ae0e0e0e (partial: some found)
  - `case_refu_014`: missing a1111111 (partial: some found)
  - `case_refu_015`: missing dddddddd (partial: some found)
  - `case_refu_016`: missing ffffffff (partial: some found)
  - `case_retu_002`: missing a3333333 (partial: some found)
  - `case_retu_005`: missing bcccccc1, cccccccc (partial: some found)
  - `case_retu_006`: missing bcccccc1 (partial: some found)
  - `case_retu_007`: missing 33333333, a4444444
  - `case_retu_010`: missing ad0d0d0d (partial: some found)
  - `case_retu_011`: missing a9999999, eeeeeeee (partial: some found)
  - `case_tech_002`: missing aaaaaaaa (partial: some found)
  - `case_tech_003`: missing ad0d0d0d, ad0d0d0d (partial: some found)
  - `case_tech_004`: missing aaaaaaaa (partial: some found)

Possible causes: query underspecification (query expansion), RRF dual-source bias (fusion tuning), or knowledge-record-term mismatch (keyword gap).

- **15 unlabeled cases** — cannot be evaluated at doc-ID granularity. See manual review report for details.

### Recommendations

1. **Archive Phase 10** — metric granularity thesis confirmed across full labeled dataset.
2. **Query expansion audit** — for the remaining true misses, check if query underspecifies the needed knowledge.
3. **Fusion ranking experiment** — for cases where doc_id found but below top-10, tune RRF or add reranker.
4. **Portfolio snapshot** (Phase 10.8) — update with full-dataset real pipeline metrics.
