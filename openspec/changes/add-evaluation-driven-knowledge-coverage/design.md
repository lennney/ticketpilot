# Design: Evaluation-driven Knowledge Coverage Optimization (Phase 9)

## Architecture Constraints

### Immutable Baselines

Phase 7 and Phase 8 baseline reports are read-only for Phase 9. No modification to:

- `reports/retrieval/fake_vs_real_comparison.{json,md}` (Phase 8)
- `reports/retrieval/wrong_cases.md` (Phase 8)
- `reports/retrieval/fake_retrieval_rows.json` (Phase 8)
- `reports/retrieval/real_retrieval_rows.json` (Phase 8)
- `reports/evaluation/*` (Phase 7)

Phase 9 creates new reports under `reports/retrieval/phase9_*` or equivalent namespaced paths.

### Provider Architecture (Unchanged)

| Aspect | Phase 7 | Phase 8 | Phase 9 |
|--------|---------|---------|---------|
| Default provider | FakeEmbeddingProvider (384-d) | FakeEmbeddingProvider (384-d) | FakeEmbeddingProvider (384-d) |
| Real provider | N/A | Opt-in via EMBEDDING_PROVIDER=real | Opt-in via EMBEDDING_PROVIDER=real |
| Provider interface | Protocol | Protocol | Unchanged |
| Dimension contract | Fake=384 | Real=1024, enforced | Unchanged |

Phase 9 does not add, remove, or reconfigure embedding providers.

### Knowledge Source Layers (Unchanged)

```
knowledge_faq    ──→ knowledge_chunks (doc_type=FAQ)
knowledge_policy ──→ knowledge_chunks (doc_type=POLICY)
knowledge_case   ──→ knowledge_chunks (doc_type=CASE)
```

- FAQ / Policy / Case physical table separation preserved
- Parent-child chunking retained
- 1 source record ≈ 1 retrieval chunk for current short records (no chunk splitting needed yet)

### Retrieval Pipeline (Unchanged)

```
query → keyword (ts_vector) + vector (cosine) → RRF fusion → top-10
```

No changes to `retrieve_evidence.py`, `query_builder.py`, `chunker.py`, `rrf.py`, or `vector_search.py`.

### Evaluation Architecture (New Comparison Layer)

Phase 9 adds a new comparison dimension:

```
Phase 8 baseline (95 records)  vs  Phase 9 expanded (95 + N records)
                                    │
                          same 101 eval tickets
                          same provider (fake or real)
                          same retrieval pipeline
                          same metrics (Top-K, MRR, wrong cases)
```

The comparison is: **knowledge base size**, not embedding provider.

## Data Flow

```
Phase 8 wrong_cases.md (41 cases)
        │
        ▼
Taxonomy refinement ──→ Categorized gap analysis
        │
        ▼
Knowledge coverage gap mapping ──→ per-case knowledge needs
        │
        ▼
Targeted FAQ/Policy/Case expansion ──→ new seed records (synthetic/adapted)
        │
        ▼
Doc-level golden labels (optional) ──→ enriched golden_expectations.csv
        │
        ▼
Pipeline-backed evaluation rerun ──→ Phase 9 metrics
        │
        ▼
Before-vs-after comparison ──→ Phase 9 report + portfolio snapshot
```

## Wrong-Case Taxonomy Design

Phase 8 uses a single category (`missing_doc_type`). Phase 9 refines into:

| Category | Definition | Actionable? |
|----------|------------|-------------|
| `missing_faq` | No FAQ record covers the intent/domain combination | Add FAQ |
| `missing_policy` | No Policy record covers the rule/compliance topic | Add Policy |
| `missing_case` | No Case record covers the scenario/precedent | Add Case |
| `doc_type_mismatch` | Retrieved docs exist but wrong type (e.g., FAQ instead of Policy) | Review query construction |
| `business_domain_gap` | Entire business domain has sparse/no coverage | Add cross-type records |
| `risk_level_gap` | Knowledge lacks records annotated at required risk level | Add risk-tagged records |
| `query_expansion_gap` | Retrieval query is underspecified for the knowledge that exists | Improve query builder |
| `golden_label_gap` | Golden expectations are incomplete (empty or too narrow) | Fix golden labels |

## Knowledge Expansion Design

### Source Rules (Phase 7 Data Strategy)

- Synthetic: written by developer based on Chinese e-commerce domain knowledge
- Adapted: derived from public e-commerce policy documentation, reworded
- Public-source-inspired: based on common CS scenarios, not proprietary data
- **No real customer data ever**

### Expansion Process

1. For each wrong case, identify what knowledge would have helped
2. Determine doc type (FAQ/Policy/Case) and business domain
3. Write synthetic/adapted record following existing schema
4. Add to `data/knowledge/{faq,policy,case}_seed.json`
5. Rebuild embeddings (fake or real, consistent with evaluation run)
6. Document in gap report which case(s) each record addresses

### Traceability

Each new knowledge record should have a documented relationship to the wrong case(s) it helps address. This can be tracked in a gap mapping document, not in the database schema.

## Doc-Level Golden Labels (Optional Enhancement)

Current golden expectations use `expected_evidence_doc_types` (e.g., `["FAQ", "Policy"]`). Phase 9 may optionally add `expected_relevant_doc_ids` to enable:

- Recall@K at document level (not just doc type level)
- More precise wrong-case classification
- Distinguishing "right doc type, wrong specific doc" from "wrong doc type entirely"

If doc-level labels are added, they are additive — existing `expected_evidence_doc_types` remain the primary expectation.

## Safety Constraints

- Human-in-the-loop required for risk flags (unchanged from Phase 7)
- No auto-send, no auto-reply (unchanged)
- High-risk / insufficient-evidence cases trigger human review (unchanged)
- No production or real customer data (unchanged)
- Secret scan must remain clean (unchanged)

## File Manifest (Planning Stage)

| File | Purpose | This Batch? |
|------|---------|-------------|
| `proposal.md` | Problem, goal, non-goals, scope, risks | Exists |
| `design.md` | Architecture constraints, data flow, taxonomy design | Created now |
| `tasks.md` | Task breakdown for all 7 sub-phases | Created now |
| `specs/retrieval-evaluation/spec.md` | Wrong-case taxonomy, doc-level labels, Phase-9 comparison | Created now |
| `specs/knowledge-schema/spec.md` | Knowledge expansion traceability, seed data rules | Created now |
