# Phase 9.4.1 P0 Added-Record Hit Audit

*Generated at 2026-05-05*
*Part of Phase 9.5.1 — Evaluation Semantics Repair + P0 Audit*

## Summary

| Metric | Count |
|--------|-------|
| P0 records audited | 11 (1 FAQ + 4 Policy + 6 Case) |
| Record-case pairs checked | 16 (across 15 related wrong cases) |
| Records in related case Top-10 | 3/16 (18.8%) |
| **Wrong cases fixed by P0 records** | **0** |

## Key Finding

**All 3 hits are partial**: the P0 record entered the Top-10 for its related wrong case,
but the case still fails because the other expected doc type remains missing.

### Detailed Hit Analysis

| # | P0 Record ID | Type | Related Case | P9 Rank | Expected Types | Missing Type | Why Still Fails |
|---|-------------|------|-------------|---------|---------------|-------------|-----------------|
| 1 | `ae0e0e0e-bbbb-...` | POLICY | case_acco_003 | Top-3 | Case, Policy | Case | Policy hit but no Case doc type |
| 2 | `ae0e0e0e-dddd-...` | POLICY | case_refu_009 | Top-2 | Case, Policy | Case | Policy hit but no Case doc type |
| 3 | `ca0a0a0a-6666-...` | CASE | case_refu_013 | Top-9 | Case, Policy | Policy | Case hit but no Policy doc type |

## Record-by-Record Audit Table

| New Record ID | Type | Gap ID | Related Wrong Cases | P9 Top-10? | Best Rank | Interpretation |
|---|---|---|---|---|---|---|
| `f0f0f0f0-2222...` | FAQ | KG-FAQ-003 | case_retu_004 | MISS | — | Record not in top-10; case expects Case+Policy, FAQ alone insufficient |
| `ae0e0e0e-aaaa...` | POLICY | KG-POL-001 | case_refu_001 | MISS | — | Refund escalation policy not surfaced |
| `ae0e0e0e-aaaa...` | POLICY | KG-POL-001 | case_refu_006 | MISS | — | Same policy, different case — not surfaced |
| `ae0e0e0e-bbbb...` | POLICY | KG-POL-003 | case_acco_003 | **HIT** | **3** | Privacy policy surfaced but case still needs Case doc type |
| `ae0e0e0e-bbbb...` | POLICY | KG-POL-003 | case_acco_006 | MISS | — | Same policy, different account case — not surfaced |
| `ae0e0e0e-bbbb...` | POLICY | KG-POL-003 | case_acco_012 | MISS | — | Same policy, different account case — not surfaced |
| `ae0e0e0e-cccc...` | POLICY | KG-POL-002 | case_refu_013 | MISS | — | Counterfeit policy not surfaced; Case doc hit at rank 9 |
| `ae0e0e0e-dddd...` | POLICY | KG-POL-005 | case_refu_009 | **HIT** | **2** | Legal-threat policy surfaced but case still needs Case doc type |
| `ca0a0a0a-5555...` | CASE | KG-CASE-001 | case_comp_001 | MISS | — | Agent complaint case not surfaced |
| `ca0a0a0a-6666...` | CASE | KG-CASE-002 | case_comp_002 | MISS | — | Counterfeit case not surfaced in comp_002 |
| `ca0a0a0a-6666...` | CASE | KG-CASE-002 | case_refu_013 | **HIT** | **9** | Counterfeit case surfaced but case still needs Policy doc type |
| `ca0a0a0a-7777...` | CASE | KG-CASE-003 | case_comp_003 | MISS | — | Promotion case not surfaced |
| `ca0a0a0a-8888...` | CASE | KG-CASE-006 | case_comp_008 | MISS | — | After-sales case not surfaced |
| `ca0a0a0a-9999...` | CASE | KG-RISK-001 | case_comp_004 | MISS | — | Legal-threat case not surfaced in comp_004 |
| `ca0a0a0a-9999...` | CASE | KG-RISK-001 | case_comp_009 | MISS | — | Legal-threat case not surfaced in comp_009 |
| `ca0a0a0a-aaaa...` | CASE | KG-RISK-003 | case_acco_003 | MISS | — | Privacy case not surfaced; Policy hit at rank 3 |

## Why Fake Embeddings Limit This Audit

- **Fake embeddings are deterministic random** — document content has zero influence on ranking.
  A new record's rank depends entirely on its hash-derived position in vector space, not on
  semantic relevance to the query.
- **Keyword search is the primary retrieval path** for these cases. The P0 records use
  domain-specific terms (e.g., "假货鉴定", "律师函", "骚扰电话") that may or may not match
  the query's extracted keywords.
- **The 3 "hits" are coincidental** under fake embeddings — they do NOT indicate that the
  record's content is semantically relevant to the query.

## What a Real Provider Would Change

Under a real embedding provider (e.g., text-embedding-v4), we would expect:
- Records with semantically relevant content to rank closer to their intended queries
- The 3 partial hits might become full fixes if the other expected doc type also surfaces
- Some of the 13 MISSes might become HITs if the record's semantic content matches the query

## Bottom Line

**This audit is inconclusive for semantic impact**, same as the Phase 9.5 evaluation rerun.
P0 records exist in the knowledge base and their document types are correct, but fake embeddings
cannot meaningfully rank them for their intended queries. A real-provider rerun is required to
measure whether these records fix their targeted wrong cases.
