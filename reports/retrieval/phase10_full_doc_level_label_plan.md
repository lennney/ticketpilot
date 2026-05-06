# Phase 10.7 — Full-Dataset Doc-Level Golden Label Plan

*Generated at 2026-05-06 UTC*
*Part of Phase 10: Hybrid Retrieval Ranking Diagnosis*

## Current State

| Metric | Value |
|---|---|
| Total eval cases | 101 |
| Cases with doc-level labels (existing) | **14** |
| Cases needing labels | **87** |
| Knowledge seed FAQ records | 32 |
| Knowledge seed POLICY records | 20 |
| Knowledge seed CASE records | 21 |
| Total knowledge records | 73 |

## Labeling Strategy

### High-Confidence Criteria

A case is labeled automatically when:

1. **Expected issue type matches a knowledge business domain** (refund → refund FAQ/Policy, account_issue → account FAQ/Policy, etc.)
2. **Expected evidence doc_types** (FAQ, Policy, Case) have corresponding records with matching domain content
3. **Doc content directly supports the ticket's expected resolution path** — the knowledge record addresses the specific question or situation described in the ticket
4. **No conflict with existing golden expectation** — the label adds evidence docs that support the expected behavior
5. **Doc_id exists in seed knowledge** — confirmed against faq_seed.json / policy_seed.json / case_seed.json

### Manual-Review Criteria

Cases are sent to manual review when:

1. **No matching knowledge record exists** for the issue (e.g., job inquiries, store locations, WeChat groups)
2. **Ticket is too broad** (e.g., general product comparison)
3. **Edge cases** with minimal or special-character-only text
4. **Multiple plausible docs but no clear primary evidence** — hard to determine which doc is the "relevant" one
5. **Expected doc_type and available docs conflict** — expected evidence type has no matching records

### Doc-ID Source Tables

| Source File | Doc ID Pattern | Count |
|---|---|---|
| `data/knowledge/faq_seed.json` | `*` (various UUIDs) | 32 |
| `data/knowledge/policy_seed.json` | `a*`, `ae*`, `ad*`, `ab*`, `ac*` | 20 |
| `data/knowledge/case_seed.json` | `b*`, `c*`, `ca*` | 21 |

### CSV Compatibility Plan

- Backward compatible: empty `expected_relevant_doc_ids` is already handled by loader
- Multiple doc_ids use semicolon separator (existing convention)
- No schema changes needed
- No column reordering

## Labeling Results

See updated `data/eval/golden_expectations.csv` for full label data.
See `phase10_full_doc_level_manual_review.md` for cases sent to manual review.

## Domain-to-Knowledge Mapping

| Business Domain | FAQ Records | POLICY Records | CASE Records |
|---|---|---|---|
| refund | 11111111, 22222222, dddddddd-1111, dddddddd-2222, dddddddd-9999, eeeeeeee-8888, eeeeeeee-9999, ffffffff-2222, ffffffff-9999 | a1111111, a2222222, accccccc, ad0d0d0d-2222, ae0e0e0e-2222, ae0e0e0e-aaaa, ae0e0e0e-cccc, ae0e0e0e-dddd, ae0e0e0e-8888, ae0e0e0e-9999, ae0e0e0e-3333 | b1111111, b2222222, c6666666, c7777777, ca0a0a0a-1111, ca0a0a0a-2222, c1111111, c2222222, c3333333 |
| return_exchange | 33333333, cccccccc-cccc, dddddddd-3333, dddddddd-4444, ffffffff-3333, ffffffff-5555, f0f0f0f0-2222 | a3333333, a4444444, ad0d0d0d-1111, ae0e0e0e-4444 | b3333333, bcccccc1, c9999999 |
| account | 44444444, 55555555, eeeeeeee-2222, eeeeeeee-3333, eeeeeeee-4444, eeeeeeee-5555, ffffffff-6666 | a5555555, a6666666, ad0d0d0d-6666, ad0d0d0d-7777, ae0e0e0e-bbbb, ae0e0e0e-7777 | b4444444, b5555555, c4444444, c5555555, ca0a0a0a-aaaa |
| technical | 66666666, bbbbbbbb, f0f0f0f0-1111, eeeeeeee-1111 | aaaaaaaa | b6666666, b7777777, ca0a0a0a-3333 |
| product_consulting | 77777777, ffffffff-1111, ffffffff-8888 | abbbbbbb | bbbbbbbb |
| logistics | 88888888, 99999999, dddddddd-5555, dddddddd-6666, ffffffff-7777 | a7777777, a8888888, ae0e0e0e-6666 | b8888888, b9999999, c8888888, b2222222 |
| complaint | aaaaaaaa, eeeeeeee-6666, eeeeeeee-7777, ffffffff-4444 | a9999999, ad0d0d0d-8888, ad0d0d0d-9999, ae0e0e0e-1111 | baaaaaa, c1111111, c2222222, c3333333, ca0a0a0a-4444, ca0a0a0a-5555, ca0a0a0a-6666, ca0a0a0a-7777, ca0a0a0a-8888, ca0a0a0a-9999 |
| invoice (other) | dddddddd-7777, dddddddd-8888 | ad0d0d0d-3333 | c7777777 |
| billing (other) | dddddddd-9999, eeeeeeee-1111, ffffffff-9999 | ad0d0d0d-4444, ad0d0d0d-5555, ae0e0e0e-8888 | c6666666, ca0a0a0a-7777, b7777777 |
