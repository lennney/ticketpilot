# Phase 9.4.0 — Knowledge Data Schema / Seed Flow Audit

*Generated at 2026-05-05 UTC*
*Part of Phase 9: Evaluation-driven Knowledge Coverage Optimization*
*OpenSpec Change: add-evaluation-driven-knowledge-coverage*

> **Boundary statements:**
> - This is an audit-only document. No data, src, or test files are modified.
> - All 101 eval tickets and 95 knowledge records are synthetic / adapted / public-source-inspired.
> - Phase 9.4 knowledge expansion will add synthetic records only — no real customer data.
> - No embeddings rebuilt, no database changes, no baseline report modifications.

---

## 1. Knowledge Seed File Inventory

| File | Purpose | Record Type | Current Count | Phase 9.4 Modify? | Notes |
|---|---|---|---:|---|---|
| `data/knowledge/faq_seed.json` | FAQ knowledge records | FAQ | 40 | ✅ Add 1-3 | UUID-based, each ≈1 parent chunk |
| `data/knowledge/policy_seed.json` | Policy knowledge records | Policy | 30 | ✅ Add 5-7 | UUID-based, policy_code `X.Y.Z` format |
| `data/knowledge/case_seed.json` | Case knowledge records | Case | 25 | ✅ Add 10-13 | UUID-based, has risk_level + compensation |
| `data/eval/tickets_eval.csv` | Eval tickets (101) | CSV | 101 | ❌ No | Phase 7/8 baseline — immutable |
| `data/eval/golden_expectations.csv` | Golden expectations | CSV | 101 | ❌ No | Needs golden_label_gap fix but in non-knowledge workstream |
| `data/eval/sample_predictions.csv` | Sample predictions | CSV | — | ❌ No | Used by evaluation tooling |
| `data/eval/adaptation_candidates.csv` | Source adaptation | CSV | — | ❌ No | Already processed — not needed |

**Source scripts that consume seed data:**

| Script | Role | Phase 9.4 Relevance |
|---|---|---|
| `scripts/ingest_knowledge.py` | Load seed JSON → chunk → print stats (no DB needed) | ✅ Run to verify new records |
| `scripts/rebuild_embeddings.py` | Rebuild embeddings in DB (requires --confirm) | ✅ Phase 9.5 only |
| `scripts/run_eval.py` | Offline evaluation (in-memory, no DB) | ✅ Phase 9.5 only |
| `scripts/run_retrieval_comparison.py` | Retrieval comparison (mock/export/compare) | ✅ Phase 9.5 only |

---

## 2. Schema and Required Fields

### Source Record Schemas

| Layer | Required Fields | Optional Fields | Validation Source |
|---|---|---|---|
| **FAQ** | `id` (UUID, auto), `doc_type` (FAQ, frozen), `business_domain`, `title`, `content` | `intent_tags`, `created_at`, `updated_at` | `FAQDocument` in `schema/knowledge.py` |
| **Policy** | `id` (UUID, auto), `doc_type` (POLICY, frozen), `business_domain`, `policy_code` (`X.Y.Z`), `title`, `content`, `effective_date` | `created_at`, `updated_at` | `PolicyDocument` in `schema/knowledge.py` |
| **Case** | `id` (UUID, auto), `doc_type` (CASE, frozen), `business_domain`, `case_id`, `issue_summary`, `resolution`, `risk_level` | `compensation_amount`, `created_at`, `updated_at` | `CaseDocument` in `schema/knowledge.py` |
| **KnowledgeChunk** | `id` (UUID, auto), `doc_id`, `doc_type`, `source_table`, `source_id`, `chunk_level` (1=PARENT/2=CHILD), `business_domain`, `content`, `content_hash` (SHA-256, 64 hex) | `parent_chunk_id`, `risk_level`, `created_at` | `KnowledgeChunk` in `schema/knowledge.py` |

### Enum Constants

| Enum | Valid Values | Notes |
|---|---|---|
| `DocType` | `FAQ`, `POLICY`, `CASE` | Frozen per document — validated by Pydantic |
| `ChunkLevel` | `PARENT` (1), `CHILD` (2) | |
| `BusinessDomain` | `refund`, `return_exchange`, `account`, `technical`, `product_consulting`, `logistics`, `complaint`, `other` | 8 values total |
| `RiskLevel` | `low`, `medium`, `high` | Required for Case, optional for Chunk |

### Current Business Domain Coverage Per Seed File

| Domain | FAQ (40) | Policy (30) | Case (25) |
|---|---|---|---|
| refund | ✅ | ✅ | ✅ |
| return_exchange | ✅ | ✅ | ✅ |
| account | ✅ | ✅ | ✅ |
| technical | ✅ | ✅ | ✅ |
| product_consulting | ✅ | — | — |
| logistics | ✅ | ✅ | ✅ |
| complaint | ✅ | ✅ | ✅ |
| other | ✅ | — | — |

### Key Traceability Fields on KnowledgeChunk

The `KnowledgeChunk` model tracks the two-layer architecture:

```
source_table → "knowledge_faq" | "knowledge_policy" | "knowledge_case"
source_id    → UUID of the row in the source table
parent_chunk_id → NULL for PARENT, UUID of parent for CHILD
```

### Embedding Behavior

- **Default provider:** `FakeEmbeddingProvider` (384-d, deterministic SHA-256 seeded)
- **Real provider:** `openai_compatible` (opt-in via `EMBEDDING_PROVIDER` env var)
- **No embedding in seed JSON** — embeddings are generated at DB ingestion time by `seeding.py`
- **Phase 9.4 does NOT need to regenerate embeddings** until Phase 9.5 evaluation rerun

---

## 3. Current Tests and Validation Commands

### Directly Relevant (test knowledge schema, seed data, chunking)

| Test File | What It Validates | Run in Phase 9.4? | Risk |
|---|---|---|---|
| `tests/unit/test_knowledge_schema.py` | DocType, ChunkLevel, BusinessDomain, RiskLevel enums; FAQDocument, PolicyDocument, CaseDocument, KnowledgeChunk validation | ✅ After each record addition | Low |
| `tests/unit/test_seed_data.py` | Seed files exist, record counts ≥10, doc_type frozen, policy_code format, domain coverage ≥4 | ✅ After each record addition | Low |
| `tests/unit/test_chunking.py` | Content hash computation, sentence boundary detection, parent-child chunking logic | ✅ After chunker changes (not needed for Phase 9.4) | Low |

### Indirectly Relevant (evaluation, retrieval)

| Test File | What It Validates | Run in Phase 9.4? | Risk |
|---|---|---|---|
| `tests/unit/test_retrieval_metrics.py` | Top-K hit rate, MRR, wrong-case classification | ❌ After Phase 9.5 evaluation rerun | Low |
| `tests/unit/test_retrieval_comparison.py` | Retrieval comparison report generation | ❌ After Phase 9.5 | Low |
| `tests/unit/test_evaluation_*.py` | Eval dataset loading, metrics, prediction loading, reporting | ❌ After Phase 9.5 | Low |
| `tests/unit/test_fake_embedding.py` | Determinism and statistical properties | ❌ Only if embedding provider changes | Low |

### Validation Commands for Phase 9.4

```bash
# Run knowledge schema tests (fast, ~5 sec)
uv run pytest tests/unit/test_knowledge_schema.py -v --tb=short

# Run seed data tests (loads all seed JSON, validates content)
uv run pytest tests/unit/test_seed_data.py -v --tb=short

# Run chunking tests (only if chunker logic changes)
uv run pytest tests/unit/test_chunking.py -v --tb=short

# Dry-run ingestion (prints stats without DB)
uv run python scripts/ingest_knowledge.py
```

---

## 4. Ingestion / Rebuild Flow

### Current Flow (no DB required for seed validation)

```
data/knowledge/faq_seed.json    ─┐
data/knowledge/policy_seed.json  ├─→ seeds.py (Pydantic validation)
data/knowledge/case_seed.json   ─┘       │
                                         ▼
                                  knowledge_chunker.py
                                  (parent-child chunking)       ─→ KnowledgeChunk objects
                                         │
                                         ▼
                                  scripts/ingest_knowledge.py
                                  (print stats, no DB write)
```

### Full Flow (with DB, for Phase 9.5 evaluation rerun)

```
seed JSON → seeds.py → chunker → seeding.py → DB (knowledge_faq/policy/case + knowledge_chunks)
                                                      │
                                                      ▼
                                              rebuild_embeddings.py
                                              (fake: 384-d, real: opt-in)
                                                      │
                                                      ▼
                                              run_retrieval_comparison.py
                                              → reports/retrieval/phase9_*
```

### Phase 9.4 Constraints Confirmed

| Question | Answer |
|---|---|
| Modify seed JSON files? | ✅ Yes — `data/knowledge/faq_seed.json`, `policy_seed.json`, `case_seed.json` |
| Run seed/import script? | Optional — `scripts/ingest_knowledge.py` for stats verification |
| Rebuild knowledge_chunks? | Not needed for seed files (chunked at DB ingestion time) |
| Rebuild embeddings? | ❌ Not in Phase 9.4 — deferred to Phase 9.5 |
| Fake provider default? | Yes — `EMBEDDING_PROVIDER=fake` is default |
| Affect Phase 7/8 baseline reports? | ❌ No — Phase 9 writes to `reports/retrieval/phase9_*` paths |
| Phase 9 comparison layer? | New `phase9_*` reports, separate from `fake_vs_real_comparison.*` |

---

## 5. Phase 9.4 P0 Mini-Batch Proposal

Based on `reports/retrieval/phase9_knowledge_gap_map.md` priority order. First batch ≤12 records.

### Selection Criteria

- Directly addresses ≥1 wrong case
- P0 priority per gap map
- Business domain with highest wrong rate (complaint 77%, refund 50%)
- Balanced doc_type distribution

### Proposed P0 Batch (10-11 records)

| ID | Target Doc Type | Gap ID | Related Wrong Cases | Business Domain | Risk Level | Proposed Knowledge Need | Why P0 |
|---|---|---|---|---|---|---|---|
| FAQ-P0-01 | FAQ | KG-FAQ-003 | retu_004 | return_exchange | low | Exchange-out-of-stock: what options customer has when requested exchange item is out of stock | Only missing_faq case. Simple, narrow, high certainty of impact. |
| POL-P0-01 | Policy | KG-POL-001 | refu_001, refu_006 | refund | medium | Refund delay escalation: policy about complaint escalation path and processing timeline when refund exceeds standard window | Addresses 2 refund wrong cases. refund=50% wrong rate. |
| POL-P0-02 | Policy | KG-POL-003 | acco_003, acco_006, acco_012 | account | high | Privacy leak / identity theft: policy about personal data breach handling, identity verification, and platform liability boundary | Addresses 3 account wrong cases. HIGH-risk privacy domain. |
| POL-P0-03 | Policy | KG-POL-002 | refu_013 | refund | high | Counterfeit goods: policy about authentication procedure, compensation rules, and police reporting obligations | HIGH-risk refund + counterfeit gap. Needed by KG-CASE-002 too. |
| POL-P0-04 | Policy | KG-POL-005 | refu_009 (partial) | refund | high | Legal threat handling: policy about refund processing boundary when customer issues legal threats, and legal team handoff rules | Pairs with cross-type KG-MIX-001. HIGH legal_risk. |
| CASE-P0-01 | Case | KG-CASE-001 | comp_001 | complaint | medium | Customer complaint about agent attitude: resolution with apology + retraining + compensation | complaint=77% wrong rate. Most common complaint scenario. |
| CASE-P0-02 | Case | KG-CASE-002 | comp_002, refu_013 | complaint / refund | high | Counterfeit goods accusation: investigation + refund + compensation | Covers 2 wrong cases across complaint + refund. HIGH risk. |
| CASE-P0-03 | Case | KG-CASE-003 | comp_003 | complaint | medium | Promotion discount not honored: complaint handling and partial compensation | Common e-commerce complaint scenario. |
| CASE-P0-04 | Case | KG-CASE-006 | comp_008 | complaint | medium | After-sales channel unreachable: escalation procedure when phone+online support both down | Covers a critical service failure scenario. |
| CASE-P0-05 | Case | KG-RISK-001 | comp_004, comp_009 | complaint | high | Legal threat + written apology demand + large compensation: HIGH-risk escalation process | Addresses HIGH-risk gap. comp_004 + comp_009 both legal_risk. |
| CASE-P0-06 | Case | KG-RISK-003 / KG-POL-003 | acco_003 | account | high | Phone number leak leading to harassment: platform investigation + user protection | HIGH-risk privacy incident. Pairs with POL-P0-02. |

**Totals in this batch:** FAQ 1 + Policy 4 + Case 6 = **11 records**
- Addresses 13 unique wrong cases (some overlap with gap IDs)
- Covers: complaint (6), refund (3), account (2), return_exchange (1), HIGH-risk (4), MEDIUM-risk (4)

### Deferred to Later Batches

| Reason | Records |
|---|---|
| P1 priority (logistics, return exchange escalation) | CASE-P1: logi_008, retu_006, retu_010, retu_011 |
| P1 priority (invoice disputes) | POL-P1: othe_011, othe_012, othe_013 |
| Cross-type / business domain gaps (require coordinated multi-type) | KG-MIX-001/002/003 (legal threat, ID theft, data leak) |
| Preventive only (comp_010, comp_011) | FAQ preventive: UI navigation, accessibility |

---

## 6. Traceability Requirements

Every knowledge record added in Phase 9.4 MUST include the following traceability fields (in the JSON seed file or a companion manifest):

| Traceability Field | Required | Source | Example |
|---|---|---|---|
| `related_gap_id` | ✅ | Phase 9.3 gap map | `KG-CASE-001` |
| `related_wrong_case_ids` | ✅ | Phase 9.2 taxonomy | `["comp_001", "comp_002"]` |
| `target_doc_type` | ✅ | Schema knowledge.py | `FAQ`, `POLICY`, `CASE` |
| `business_domain` | ✅ | Schema knowledge.py | `complaint`, `refund` |
| `risk_level` | ✅ (if Case) | Schema knowledge.py | `high`, `medium`, `low` |
| `synthetic_source_note` | ✅ | Audit requirement | `"Synthetic — based on Chinese e-commerce customer service domain knowledge"` |
| `expected_evidence_behavior` | ✅ | Evaluation spec | `"This Case should be retrieved as evidence for counterfeit-goods complaint scenarios"` |
| `golden_label_needs_review` | ⚠️ If applicable | Phase 9.3 non-knowledge | Boolean — does this record need a golden_expectations.csv update? |
| `query_expansion_needs_review` | ⚠️ If applicable | Phase 9.3 non-knowledge | Boolean — does this record's retrieval need query builder changes? |

### Traceability Manifest Format

The recommended approach is to update the seed JSON files directly (they already contain `id`, `doc_type`, `business_domain`, etc.) and keep traceability in a separate companion file or inline comment convention. Since JSON does not support comments, a companion markdown table or CSV should be maintained in `reports/retrieval/phase9_knowledge_traceability.md`.

### Schema Compatibility Checklist

Before adding any record, verify:
- [ ] UUID is unique (not conflicting with existing IDs in seed files)
- [ ] `doc_type` matches the target file (FAQ file → FAQ only)
- [ ] `business_domain` is one of the 8 valid enum values
- [ ] `risk_level` is present for Case records
- [ ] Policy `policy_code` follows `X.Y.Z` format
- [ ] Content length is reasonable (< 1000 chars for single parent chunk, or document will be split)
- [ ] Content does not contain real customer PII, API keys, or secrets
- [ ] The record addresses a specific gap ID from Phase 9.3

---

## 7. Non-knowledge Workstream Prerequisites

Before Phase 9.4 knowledge records are written, these non-knowledge fixes should be applied:

| Workstream | Prerequisite | Status | Phase |
|---|---|---|---|
| `golden_label_gap` (4 edge cases) | Add `expected_evidence_doc_types` to `golden_expectations.csv` | ❌ Pending | Before 9.4.1 or parallel |
| `query_expansion_gap` (4 cases) | Review `build_retrieval_query()` output | ❌ Pending | Parallel to 9.4.1 |
| `doc_type_mismatch` (2 cases) | Audit RRF fusion weights | ❌ Pending | After 9.4.1 evaluation |
| `needs_manual_review` (edge_002) | Manual trace review | ❌ Pending | Before or during 9.4.1 |

---

## 8. Validation Boundary

- ✅ `reports/retrieval/phase9_knowledge_seed_audit.md` — new audit report (this file)
- ✅ `openspec/changes/add-evaluation-driven-knowledge-coverage/tasks.md` — Phase 9.4.0 tasks marked complete
- ✅ `docs/changelog.md` — Phase 9.4.0 audit entry
- ❌ No `src/` files modified
- ❌ No `tests/` files modified
- ❌ No `data/` files modified
- ❌ No database / migration files modified
- ❌ No `docs/portfolio/` files modified
- ❌ No Phase 7/8 baseline reports modified
- ❌ No embeddings rebuilt
- ❌ No `pyproject.toml`, `uv.lock`, `.env`, `.env.local` changes
- ❌ No real customer data referenced
- ❌ No raw external datasets scraped or imported
- ❌ No secrets exposed
