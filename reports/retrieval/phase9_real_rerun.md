# Phase 9 Real-Provider Evaluation Rerun — Knowledge Expansion Impact

*Generated at 2026-05-05 12:26 UTC*

## Overview

Phase 9.4.1 added 11 P0 knowledge records (FAQ+1, Policy+4, Case+6) to close identified
knowledge gaps. This report compares retrieval metrics **before** (Phase 8 real baseline,
95 records) and **after** (Phase 9 real expanded, 106 records), using real semantic
embeddings from dashscope (`text-embedding-v4`, 1024-dim) on 101 eval tickets.

## Provider Identity (Verified)

| Run | Provider | Model | Dim | Records | File |
|-----|----------|-------|-----|---------|------|
| Phase 8 baseline | `openai_compatible` | `text-embedding-v4` | 1024 | 95 | `real_retrieval_rows.json` |
| Phase 9 expanded | `openai_compatible` | `text-embedding-v4` | 1024 | 106 | `phase9_real_retrieval_rows.json` |

Both runs confirmed real. Phase 8 real baseline identity verified via retrieval trace
(`embedding_provider=openai_compatible`) and DB metadata. See `phase9_provider_identity_audit.md`.

## Dataset

- Total eval cases: 101
- Golden expectations: `data/eval/golden_expectations.csv`
- Phase 8 real rows: `reports/retrieval/real_retrieval_rows.json` (2026-05-04, 95 records)
- Phase 9 real rows: `reports/retrieval/phase9_real_retrieval_rows.json` (2026-05-05, 106 records)

## Aggregate Metrics

### Top-K Doc Type Hit Rate

| k | Phase 8 Real (95) | Phase 9 Real (106) | Delta |
|---|-------------------|--------------------|-------|
| 1 | 42.6%             | 44.6%              | +2.0% |
| 3 | 56.4%             | 54.5%              | -2.0% |
| 5 | 58.4%             | 57.4%              | -1.0% |
| 10 | 59.4%            | 59.4%              | 0.0% |

### Mean Reciprocal Rank

| Metric | Phase 8 Real | Phase 9 Real | Delta |
|--------|-------------|-------------|-------|
| MRR (doc_type) | 0.4913 | 0.4995 | +0.0082 |

## Wrong Cases

| Metric | Phase 8 Real | Phase 9 Real |
|--------|-------------|-------------|
| Wrong cases | 41 | 41 |

### Failure Mode Distribution

| Failure Mode | Phase 8 Real | Phase 9 Real |
|--------------|-------------|-------------|
| missing_doc_type | 41 | 41 |

## P0 Added-Record Hit Audit (Real Provider)

| Metric | Fake Provider | Real Provider |
|--------|--------------|--------------|
| P0 record-case pairs | 16 | 16 |
| Hits (record in top-10) | 3 (18.8%) | **12 (75.0%)** |
| Wrong cases fixed | 0 | 0 |

### Detailed Hit Analysis

Under real semantic embeddings, 12 of 16 P0 records surface in the top-10 for their
intended queries — a 4× improvement over fake embeddings (3/16). However, zero wrong
cases were fixed because:

- **12 of 14 P0-related cases were already correct** under Phase 8 real — the
  required doc types (Policy + Case) already appeared in the top-10 before knowledge
  expansion
- **2 cases remain wrong** (`case_acco_006`, `case_comp_009`) — both missing Policy
  doc type in top-10, and the P0 Policy records didn't fix this

### Record-by-Record Hit Table

| P0 Record | Gap ID | Related Cases | Hits | Best Rank |
|-----------|--------|---------------|------|-----------|
| `f0f0f0f0-2222...` (FAQ) | KG-FAQ-003 | retu_004 | 1/1 | 5 |
| `ae0e0e0e-aaaa...` (POLICY) | KG-POL-001 | refu_001, refu_006 | 2/2 | 3, 3 |
| `ae0e0e0e-bbbb...` (POLICY) | KG-POL-003 | acco_003, acco_006, acco_012 | 2/3 | 5, 4 |
| `ae0e0e0e-cccc...` (POLICY) | KG-POL-002 | refu_013 | 0/1 | — |
| `ae0e0e0e-dddd...` (POLICY) | KG-POL-005 | refu_009 | 1/1 | 1 |
| `ca0a0a0a-5555...` (CASE) | KG-CASE-001 | comp_001 | 0/1 | — |
| `ca0a0a0a-6666...` (CASE) | KG-CASE-002 | comp_002, refu_013 | 1/2 | 2 |
| `ca0a0a0a-7777...` (CASE) | KG-CASE-003 | comp_003 | 1/1 | 2 |
| `ca0a0a0a-8888...` (CASE) | KG-CASE-006 | comp_008 | 1/1 | 1 |
| `ca0a0a0a-9999...` (CASE) | KG-RISK-001 | comp_004, comp_009 | 2/2 | 4, 5 |
| `ca0a0a0a-aaaa...` (CASE) | KG-RISK-003 | acco_003 | 1/1 | 2 |

## Analysis

### Real vs Fake: Semantic Impact is Measurable

The P0 hit rate jumped from 18.8% (fake) to 75.0% (real), confirming that semantic
embeddings meaningfully rank relevant new records. Under fake embeddings, only
coincidental vector-space proximity produced 3 hits; under real embeddings, the P0
records' domain-specific content (e.g., "假货鉴定", "律师函", "骚扰电话") matches
query intent and drives ranking.

### No Wrong Cases Fixed: Knowledge Coverage, Not Embedding Quality

Despite 12/16 P0 records landing in top-10, zero wrong cases were fixed. This is
because most P0-targeted cases (12/14) were already passing under Phase 8 real —
the required doc types were already present in the top-10. The 2 remaining wrong
cases (`case_acco_006`, `case_comp_009`) are missing Policy doc type, and the new
P0 Policy records didn't rank highly enough to fill this gap.

The bottleneck is now **knowledge coverage and retrieval ranking**, not embedding
quality. The P0 records fill content gaps but don't necessarily displace the
already-present-but-wrong-type documents in the top-10.

### Top-1 Improvement (+2.0%)

The +2.0pp Top-1 improvement is modest but directionally positive — some P0
records did reach rank 1 for their intended queries (KG-POL-005 → refu_009,
KG-CASE-006 → comp_008). This suggests knowledge expansion can improve ranking
precision for specific query patterns.

## Comparison to Phase 9 Fake Evaluation

| Metric | Fake (Phase 9.5) | Real (Phase 9.5.3) |
|--------|-----------------|---------------------|
| Top-1 delta | -5.0% | +2.0% |
| Top-3 delta | -2.0% | -2.0% |
| Top-5 delta | +1.0% | -1.0% |
| Top-10 delta | 0.0% | 0.0% |
| MRR delta | -0.0337 | +0.0082 |
| Wrong cases delta | 0 | 0 |
| P0 hit rate | 18.8% | 75.0% |

The fake evaluation falsely suggested knowledge expansion regressed Top-1 (-5%).
Real evaluation shows the opposite: +2.0% improvement. **The fake embedding
evaluation was not just inconclusive — it was directionally misleading.**

## Validation

| Check | Result |
|-------|--------|
| Provider identity audit | Phase 8 real confirmed, Phase 9 real confirmed |
| `phase9_provider_identity_audit.md` | Created |
| P0 added-record hit audit (real) | 12/16 hits, 0 wrong cases fixed |
| Real embeddings rebuilt | 106 chunks, openai_compatible, text-embedding-v4, 1024-dim |

## Limitations

- Wrong case count unchanged (41 → 41) — knowledge expansion alone insufficient
  without retrieval ranking changes or query expansion improvements
- doc_id Recall@K not available (golden lacks doc-level labels)
- 101 eval tickets — small sample for statistical significance
- Full pipeline quality (drafting, risk assessment) not measured
