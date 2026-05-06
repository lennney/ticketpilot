# Phase 10.5 — Doc-Level Golden Label Plan

*Generated at 2026-05-06 UTC*
*Part of Phase 10: Hybrid Retrieval Ranking Diagnosis*

---

## 1. Current Golden Schema

The `golden_expectations.csv` already has a column `expected_relevant_doc_ids` and the full pipeline already supports it:

| Component | Status |
|---|---|
| `GoldenExpectation.expected_relevant_doc_ids` | ✅ Already in Pydantic schema |
| `loaders.py` parser | ✅ Already parses semicolon-separated UUIDs from CSV |
| `RetrievalComparisonCase.expected_doc_ids` | ✅ Already in dataclass |
| `CaseRetrievalMetrics.top_k_doc_id_hit` | ✅ Already computed per case |
| `RetrievalComparisonSummary.hit_rate_doc_id` | ✅ Already aggregated |
| `RetrievalComparisonSummary.mrr_doc_id` | ✅ Already computed |
| `WrongCaseEntry` | ✅ Already includes per-case metrics |

**Only gap**: The CSV column exists but is empty for all 101 rows.

## 2. Proposed Schema Change

**No schema change needed.** The field already exists. Only add data to the `expected_relevant_doc_ids` column for P0-related cases.

Backward compatibility:
- Empty `expected_relevant_doc_ids` → metrics skip doc_id evaluation (existing behavior)
- Populated `expected_relevant_doc_ids` → doc_id metrics computed alongside existing doc_type metrics
- No existing column renamed or removed
- No existing golden expectation meaning changed

## 3. P0 Cases to Label

### 3.1 Cases with fused_top10_but_metric_still_wrong (12 cases)

These cases have the P0 record in final evidence — doc_id label is reliable:

| Case ID | P0 Record Doc ID | Doc Type | In Final Evidence? | Should Label? |
|---|---|---|---|---|
| case_acco_003 | ae0e0e0e-bbbb-bbbb-bbbb-bbbbbbbbbbbb | POLICY | ✅ Rank 5 | ✅ |
| case_acco_003 | ca0a0a0a-aaaa-aaaa-aaaa-aaaaaaaaaaaa | CASE | ✅ Rank 2 | ✅ |
| case_acco_012 | ae0e0e0e-bbbb-bbbb-bbbb-bbbbbbbbbbbb | POLICY | ✅ Rank 4 | ✅ |
| case_comp_003 | ca0a0a0a-7777-7777-7777-777777777777 | CASE | ✅ Rank 2 | ✅ |
| case_comp_004 | ca0a0a0a-9999-9999-9999-999999999999 | CASE | ✅ Rank 4 | ✅ |
| case_comp_008 | ca0a0a0a-8888-8888-8888-888888888888 | CASE | ✅ Rank 1 | ✅ |
| case_comp_009 | ca0a0a0a-9999-9999-9999-999999999999 | CASE | ✅ Rank 5 | ✅ |
| case_refu_001 | ae0e0e0e-aaaa-aaaa-aaaa-aaaaaaaaaaaa | POLICY | ✅ Rank 3 | ✅ |
| case_refu_006 | ae0e0e0e-aaaa-aaaa-aaaa-aaaaaaaaaaaa | POLICY | ✅ Rank 3 | ✅ |
| case_refu_009 | ae0e0e0e-dddd-dddd-dddd-dddddddddddd | POLICY | ✅ Rank 1 | ✅ |
| case_refu_013 | ca0a0a0a-6666-6666-6666-666666666666 | CASE | ✅ Rank 2 | ✅ |
| case_retu_004 | f0f0f0f0-2222-2222-2222-222222222222 | FAQ | ✅ Rank 5 | ✅ |

### 3.2 Cases with recalled_but_fused_low (3 cases)

These P0 records were recalled by vector but pushed out of fused top-10. The doc_ids are still known — labeling them measures whether they reached vector results correctly:

| Case ID | P0 Record Doc ID | Doc Type | Best Vector Rank | Should Label? |
|---|---|---|---|---|
| case_acco_006 | ae0e0e0e-bbbb-bbbb-bbbb-bbbbbbbbbbbb | POLICY | 11 | ✅ |
| case_comp_001 | ca0a0a0a-5555-5555-5555-555555555555 | CASE | 3 | ✅ |
| case_comp_002 | ca0a0a0a-6666-6666-6666-666666666666 | CASE | 2 | ✅ |

### 3.3 Cases with vector_not_recalled (1 case)

| Case ID | P0 Record Doc ID | Doc Type | Should Label? | Notes |
|---|---|---|---|---|
| case_refu_013 | ae0e0e0e-cccc-cccc-cccc-cccccccccccc | POLICY | ✅ | Confirms complete miss |

### 3.4 Total

- **14 cases** receive doc-level labels
- **16 record-case pairs** across all bottleneck types
- **No unlabeled P0 cases** (all have known doc_ids from Phase 9.4.1 seed data)

## 4. expected_relevant_doc_ids Source

All doc_ids come from the Phase 9.4.1 knowledge expansion seed data:

| Doc ID | Source File |
|---|---|
| f0f0f0f0-2222-2222-2222-222222222222 | `data/knowledge/faq_seed.json` |
| ae0e0e0e-aaaa-aaaa-aaaa-aaaaaaaaaaaa | `data/knowledge/policy_seed.json` |
| ae0e0e0e-bbbb-bbbb-bbbb-bbbbbbbbbbbb | `data/knowledge/policy_seed.json` |
| ae0e0e0e-cccc-cccc-cccc-cccccccccccc | `data/knowledge/policy_seed.json` |
| ae0e0e0e-dddd-dddd-dddd-dddddddddddd | `data/knowledge/policy_seed.json` |
| ca0a0a0a-5555-5555-5555-555555555555 | `data/knowledge/case_seed.json` |
| ca0a0a0a-6666-6666-6666-666666666666 | `data/knowledge/case_seed.json` |
| ca0a0a0a-7777-7777-7777-777777777777 | `data/knowledge/case_seed.json` |
| ca0a0a0a-8888-8888-8888-888888888888 | `data/knowledge/case_seed.json` |
| ca0a0a0a-9999-9999-9999-999999999999 | `data/knowledge/case_seed.json` |
| ca0a0a0a-aaaa-aaaa-aaaa-aaaaaaaaaaaa | `data/knowledge/case_seed.json` |

## 5. Compatibility Plan

| Concern | Mitigation |
|---|---|
| Old rows without doc_ids | The evaluation code already handles missing doc_ids — skips doc_id metrics per case. No regression. |
| UUID format validation | `_parse_semicolon_list` returns a frozenset of strings. No UUID validation needed — doc_id comparison is string-based. |
| CSV column order | `expected_relevant_doc_ids` is an optional column. If missing, the field defaults to empty frozenset. |
| Compare mode | The compare report already outputs doc_id metrics when available. No code change needed. |
| Can't confirm doc_id | All 16 doc_ids are from the Phase 9.4.1 seed data and confirmed present in the database (106 chunks, all P0 records confirmed). |
