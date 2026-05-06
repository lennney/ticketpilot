# Phase 10.5.1 — Wrong-Case Doc-ID Recheck

*Generated at 2026-05-06 02:31:52 UTC*

## Purpose

Reclassify doc-type-level wrong cases using doc-ID granularity to determine whether the remaining wrong cases are a metric granularity problem or a genuine retrieval failure.

## Summary

| Metric | Value |
|--------|-------|
| Total wrong cases (doc-type) | 41 |
| Doc-ID found in top-10 | 11 |
| Still wrong after doc-ID check | 30 |
| P0 doc-ID correct at top-10 | 10/14 |
| P0 still wrong at doc-ID level | 4 |

## Reclassified Cases (Doc-ID Found)

| Case ID | Original Failure Mode | Doc ID Found | Found Rank |
|---------|----------------------|--------------|------------|
| case_acco_003 | missing_doc_type | doc_id found | 2 |
| case_acco_012 | missing_doc_type | doc_id found | 4 |
| case_comp_003 | missing_doc_type | doc_id found | 2 |
| case_comp_004 | missing_doc_type | doc_id found | 4 |
| case_comp_008 | missing_doc_type | doc_id found | 1 |
| case_comp_009 | missing_doc_type | doc_id found | 5 |
| case_refu_001 | missing_doc_type | doc_id found | 3 |
| case_refu_006 | missing_doc_type | doc_id found | 3 |
| case_refu_009 | missing_doc_type | doc_id found | 1 |
| case_refu_013 | missing_doc_type | doc_id found | 2 |
| case_retu_004 | missing_doc_type | doc_id found | 5 |

**Conclusion**: These cases are *metric granularity* problems — the correct document 
was retrieved but the doc-type metric didn't recognize it.

## Still Wrong After Doc-ID Check

| Case ID | Original Failure Mode | Details |
|---------|----------------------|---------|
| case_acco_006 | missing_doc_type | Genuine retrieval miss |
| case_acco_009 | missing_doc_type | Genuine retrieval miss |
| case_acco_014 | missing_doc_type | Genuine retrieval miss |
| case_comp_001 | missing_doc_type | Genuine retrieval miss |
| case_comp_002 | missing_doc_type | Genuine retrieval miss |
| case_comp_005 | missing_doc_type | Genuine retrieval miss |
| case_comp_006 | missing_doc_type | Genuine retrieval miss |
| case_comp_007 | missing_doc_type | Genuine retrieval miss |
| case_comp_013 | missing_doc_type | Genuine retrieval miss |
| case_edge_001 | missing_doc_type | Genuine retrieval miss |
| case_edge_002 | missing_doc_type | Genuine retrieval miss |
| case_edge_003 | missing_doc_type | Genuine retrieval miss |
| case_edge_004 | missing_doc_type | Genuine retrieval miss |
| case_edge_005 | missing_doc_type | Genuine retrieval miss |
| case_logi_005 | missing_doc_type | Genuine retrieval miss |
| case_logi_008 | missing_doc_type | Genuine retrieval miss |
| case_logi_010 | missing_doc_type | Genuine retrieval miss |
| case_logi_011 | missing_doc_type | Genuine retrieval miss |
| case_othe_009 | missing_doc_type | Genuine retrieval miss |
| case_othe_011 | missing_doc_type | Genuine retrieval miss |
| case_othe_012 | missing_doc_type | Genuine retrieval miss |
| case_othe_013 | missing_doc_type | Genuine retrieval miss |
| case_refu_003 | missing_doc_type | Genuine retrieval miss |
| case_refu_008 | missing_doc_type | Genuine retrieval miss |
| case_refu_015 | missing_doc_type | Genuine retrieval miss |
| case_refu_016 | missing_doc_type | Genuine retrieval miss |
| case_retu_006 | missing_doc_type | Genuine retrieval miss |
| case_retu_008 | missing_doc_type | Genuine retrieval miss |
| case_retu_010 | missing_doc_type | Genuine retrieval miss |
| case_retu_011 | missing_doc_type | Genuine retrieval miss |

**Conclusion**: These cases have genuine retrieval failures — the expected doc_id 
was not in fused top-10 results. Requires deeper bottleneck investigation.

## Answer to Thesis Question

**⚠️ Thesis partially confirmed**: 11/41 (27%) of wrong cases 
are metric granularity problems. Remaining cases need deeper investigation.
