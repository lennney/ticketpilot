# Phase 10.7.5 — Remaining True Misses Analysis

*Generated at 2026-05-06 04:19:06 UTC*

## Summary

| Metric | Value |
|--------|-------|
| Total labeled cases | 86 |
| Fully correct at doc-ID level | 47 |
| Still wrong (at least 1 doc_id missing) | 39 |
| Partial hits | 32 |
| Doc-type wrong cases reclassified as doc_id-found | 32 |

## True Miss Categorization

### Query Expansion Gap (Potential)

Cases where NO expected doc_id was found in top-10 (7):

| Case ID | Expected Doc IDs | Possible Cause |
|---------|-----------------|----------------|
| case_acco_006 | ae0e0e0e | Query underspecification / keyword mismatch |
| case_acco_015 | 44444444, a5555555, ad0d0d0d | Query underspecification / keyword mismatch |
| case_comp_001 | ca0a0a0a | Query underspecification / keyword mismatch |
| case_comp_002 | ca0a0a0a | Query underspecification / keyword mismatch |
| case_logi_010 | 99999999, a8888888, b9999999 | Query underspecification / keyword mismatch |
| case_refu_012 | a1111111, ae0e0e0e, ca0a0a0a, dddddddd, eeeeeeee | Query underspecification / keyword mismatch |
| case_retu_007 | 33333333, a4444444 | Query underspecification / keyword mismatch |

### Fusion Ranking Gap (Potential)

Cases with partial hits (32):

| Case ID | Expected Doc IDs | Hit in Top-10 | Missed | Possible Cause |
|---------|-----------------|---------------|--------|----------------|
| case_acco_004 | 44444444, a5555555, ad0d0d0d, c5555555 | c5555555@7 | 44444444, a5555555, ad0d0d0d | RRF dual-source bias / low rank |
| case_acco_014 | ad0d0d0d, ae0e0e0e, ca0a0a0a, eeeeeeee | eeeeeeee@8 | ad0d0d0d, ae0e0e0e, ca0a0a0a | RRF dual-source bias / low rank |
| case_comp_007 | a9999999, b1111111, eeeeeeee | b1111111@8, eeeeeeee@6 | a9999999 | RRF dual-source bias / low rank |
| case_comp_010 | a9999999, aaaaaaaa | a9999999@7 | aaaaaaaa | RRF dual-source bias / low rank |
| case_comp_011 | a9999999, aaaaaaaa | aaaaaaaa@5 | a9999999 | RRF dual-source bias / low rank |
| case_comp_012 | a9999999, eeeeeeee | a9999999@6 | eeeeeeee | RRF dual-source bias / low rank |
| case_logi_002 | 99999999, a8888888, b2222222 | 99999999@4, b2222222@3 | a8888888 | RRF dual-source bias / low rank |
| case_logi_003 | 88888888, a7777777 | 88888888@3 | a7777777 | RRF dual-source bias / low rank |
| case_logi_011 | a8888888, ae0e0e0e, b8888888 | b8888888@4 | a8888888, ae0e0e0e | RRF dual-source bias / low rank |
| case_prod_001 | abbbbbbb, ffffffff | ffffffff@1 | abbbbbbb | RRF dual-source bias / low rank |
| case_prod_004 | abbbbbbb, ffffffff | ffffffff@2 | abbbbbbb | RRF dual-source bias / low rank |
| case_prod_008 | abbbbbbb, ffffffff | abbbbbbb@4 | ffffffff | RRF dual-source bias / low rank |
| case_refu_002 | 11111111, 22222222, a1111111, ad0d0d0d | 22222222@5, a1111111@2 | 11111111, ad0d0d0d | RRF dual-source bias / low rank |
| case_refu_003 | a3333333, ae0e0e0e, dddddddd | dddddddd@1 | a3333333, ae0e0e0e | RRF dual-source bias / low rank |
| case_refu_004 | 11111111, a1111111, ffffffff | 11111111@9, ffffffff@5 | a1111111 | RRF dual-source bias / low rank |
| case_refu_005 | 22222222, ad0d0d0d, ae0e0e0e, dddddddd | 22222222@4, ad0d0d0d@1, ae0e0e0e@5 | dddddddd | RRF dual-source bias / low rank |
| case_refu_007 | 11111111, a1111111, ffffffff | ffffffff@6 | 11111111, a1111111 | RRF dual-source bias / low rank |
| case_refu_008 | a3333333, ae0e0e0e, cccccccc | ae0e0e0e@3 | a3333333, cccccccc | RRF dual-source bias / low rank |
| case_refu_010 | a3333333, ae0e0e0e, cccccccc | a3333333@10, cccccccc@8 | ae0e0e0e | RRF dual-source bias / low rank |
| case_refu_011 | 11111111, a1111111, accccccc | a1111111@2 | 11111111, accccccc | RRF dual-source bias / low rank |
| case_refu_013 | ae0e0e0e, ca0a0a0a | ca0a0a0a@2 | ae0e0e0e | RRF dual-source bias / low rank |
| case_refu_014 | a1111111, ffffffff | ffffffff@1 | a1111111 | RRF dual-source bias / low rank |
| case_refu_015 | 22222222, ad0d0d0d, ae0e0e0e, c3333333, dddddddd | 22222222@7, ad0d0d0d@8, ae0e0e0e@4, c3333333@2 | dddddddd | RRF dual-source bias / low rank |
| case_refu_016 | ae0e0e0e, ca0a0a0a, ffffffff | ae0e0e0e@4, ca0a0a0a@2 | ffffffff | RRF dual-source bias / low rank |
| case_retu_002 | 33333333, a3333333, a4444444 | 33333333@4, a4444444@10 | a3333333 | RRF dual-source bias / low rank |
| case_retu_005 | a3333333, bcccccc1, cccccccc | a3333333@9 | bcccccc1, cccccccc | RRF dual-source bias / low rank |
| case_retu_006 | a4444444, bcccccc1, ffffffff | a4444444@4, ffffffff@1 | bcccccc1 | RRF dual-source bias / low rank |
| case_retu_010 | a3333333, ad0d0d0d, cccccccc | a3333333@8, cccccccc@5 | ad0d0d0d | RRF dual-source bias / low rank |
| case_retu_011 | a9999999, b3333333, eeeeeeee | b3333333@7 | a9999999, eeeeeeee | RRF dual-source bias / low rank |
| case_tech_002 | aaaaaaaa, bbbbbbbb | bbbbbbbb@3 | aaaaaaaa | RRF dual-source bias / low rank |
| case_tech_003 | ad0d0d0d, ad0d0d0d, b7777777, eeeeeeee | b7777777@3, eeeeeeee@1 | ad0d0d0d, ad0d0d0d | RRF dual-source bias / low rank |
| case_tech_004 | aaaaaaaa, f0f0f0f0 | f0f0f0f0@1 | aaaaaaaa | RRF dual-source bias / low rank |


## Recommended Next Steps

1. **Query expansion audit** — review query formulation for cases where no expected doc_id was found.
   Determine if query terms match knowledge record terms.
2. **Fusion ranking experiment** — for partial-hit cases, investigate if adjusting RRF k or
   score-based fusion would bring the remaining doc_ids into top-10.
3. **Manual review** — for cases where label ambiguity is suspected, verify golden labels.
