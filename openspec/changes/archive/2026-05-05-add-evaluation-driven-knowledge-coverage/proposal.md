# Proposal: Evaluation-driven Knowledge Coverage Optimization (Phase 9)

## Executive Summary

Phase 8 proved that real Chinese embedding (DashScope text-embedding-v4, 1024-d) improves evidence
ranking under fixed offline evaluation: Top-1 hit rate rose from 31.7% to 42.6% (+10.9%), MRR
improved from 0.4114 to 0.4913 (+0.0799). However, the 41 wrong cases remained identical between
fake and real, all classified as `missing_doc_type` — at least one expected document type absent
from the Top-10 results.

Phase 9 addresses the root cause identified in Phase 8: **knowledge coverage is the current
ceiling, not embedding quality.** Rather than blindly upgrading the embedding model, Phase 9
refines the wrong-case taxonomy, maps coverage gaps, adds targeted synthetic/adapted knowledge
records, and reruns offline evaluation to measure the impact.

No changes to Phase 7/8 baseline reports. No new embedding models. No production data. All
new knowledge records remain synthetic/adapted/public-source-inspired.

## Baseline (Current State after Phase 8)

### Knowledge Base
- **Total chunks**: 95
- **FAQ**: 40 records
- **Policy**: 30 records
- **Case**: 25 records
- **Source data**: Synthetic/adapted, public-source-inspired, no real enterprise data
- **Embedding**: Default FakeEmbeddingProvider (384-d); real provider is opt-in

### Retrieval Comparison Results (Phase 8)
| Metric | Fake 384-d | Real 1024-d | Delta |
|---:|---:|---:|---:|
| Top-1 hit rate | 31.7% | 42.6% | +10.9% |
| Top-3 hit rate | 47.5% | 56.4% | +8.9% |
| Top-5 hit rate | 53.5% | 58.4% | +5.0% |
| Top-10 hit rate | 59.4% | 59.4% | 0.0% |
| MRR | 0.4114 | 0.4913 | +0.0799 |
| Wrong cases | 41 | 41 | 0 |

### Wrong-Case Breakdown (Phase 8)
- **All 41 wrong cases**: `missing_doc_type`
- **Empty retrieval (4 cases)**: case_edge_002 through case_edge_005 — the query produced zero results
- **Empty expected doc types (4 cases)**: case_edge_001, case_edge_003, case_edge_004, case_edge_005 — golden file has no expected types
- **Intent distribution**: complaint 10 (77% of 13), refund 8 (50%), return 5 (45%), account 5 (33%), logistics 4 (36%), other 4 (31%), edge 5 (100%)
- **No `below_top_10` cases**: When the correct doc type is found, it's always within Top-10

## Problem

Phase 8 revealed a structural insight:

1. **Real embedding improves ranking, not coverage.** Top-1 +10.9% shows better semantic ordering,
   but Top-10 unchanged (59.4%) and wrong cases unchanged (41) show that ranking alone cannot fix
   missing content.

2. **`missing_doc_type` is too coarse.** The current taxonomy cannot distinguish between:
   - FAQ missing for this business domain
   - Policy missing for this risk type
   - Case missing for this intent class
   - Golden label gaps (wrong or incomplete expectations)
   - Query construction gaps (the query doesn't match how knowledge is written)

3. **No structured gap analysis.** Phase 8 reports list which cases are wrong but don't map them
   to actionable knowledge coverage gaps.

4. **Doc-level labels are absent.** Golden expectations only have doc type labels
   (`expected_evidence_doc_types`), not per-document IDs. This limits evaluation granularity
   and makes it harder to measure whether a specific knowledge record closes a gap.

## Goal

1. **Refine wrong-case taxonomy** beyond `missing_doc_type` into actionable categories:
   `missing_faq`, `missing_policy`, `missing_case`, `doc_type_mismatch`,
   `business_domain_gap`, `risk_level_gap`, `query_expansion_gap`, `golden_label_gap`.

2. **Map knowledge coverage gaps** from the 41 wrong cases to required FAQ/Policy/Case records.

3. **Add targeted synthetic/adapted knowledge records** covering the identified gaps,
   preserving FAQ/Policy/Case separation and parent-child traceability.

4. **Add or refine doc-level golden labels** where needed, enabling Recall@K at document level.

5. **Rerun pipeline-backed offline evaluation** on the expanded knowledge base.

6. **Compare Phase 8 baseline vs Phase 9 expanded-knowledge result** in a structured report.

7. **Produce Phase 9 portfolio snapshot** explaining the product-manager interpretation:
   "not blindly changing models, but using evaluation to identify and close knowledge coverage gaps."

## Non-Goals

- ❌ Not building a production-ready system
- ❌ Not using real enterprise customer data
- ❌ Not running online A/B tests
- ❌ Not auto-sending customer replies
- ❌ Not replacing human agents with AI
- ❌ Not introducing multi-agent role-playing
- ❌ Not restructuring chunking architecture
- ❌ Not modifying Phase 7 or Phase 8 baseline reports
- ❌ Not re-running the fake-vs-real embedding provider comparison
- ❌ Not blindly upgrading the embedding model
- ❌ Not connecting to external knowledge sources or live APIs
- ❌ Not introducing LLM-based knowledge generation
- ❌ Not making real provider the default

## Scope

### In Scope
- Wrong-case taxonomy refinement (code + schema changes to `retrieval_metrics.py`)
- Knowledge coverage gap mapping (analysis document and tooling)
- Targeted FAQ/Policy/Case knowledge expansion (new seeding data)
- Optional doc-level golden labels (`expected_relevant_doc_ids` in golden CSV)
- Pipeline-backed evaluation rerun on expanded knowledge base
- Before-vs-after comparison report (Phase 8 baseline → Phase 9 expanded)
- Wrong-case analysis comparison (improvement + persistent gaps)
- Phase 9 portfolio snapshot for product portfolio materials

### Out of Scope
- Embedding provider changes
- Chunking strategy changes
- Retrieval algorithm changes
- New evaluation metrics beyond wrong-case taxonomy
- Real-time knowledge base updates
- Automated knowledge gap detection from production data

## Success Criteria

1. **Wrong-case reduction**: `missing_doc_type` cases decrease from Phase 8 baseline (41)
2. **Ranking non-regression**: Top-1/Top-3/MRR do not regress from Phase 8 real-provider baseline
3. **Taxonomy actionability**: Each refined taxonomy category produces concrete knowledge gap recommendations
4. **Safety preservation**: High-risk/insufficient-evidence cases still trigger human review; no unsupported claim behavior introduced
5. **Data integrity**: All new knowledge records remain synthetic/adapted/public-source-inspired; no real customer data introduced
6. **Quality gate**: Full quality gate passes before archive/push (0 skipped integration tests, coverage ≥70%, secret scan clean)

## Risks

| Risk | Mitigation |
|---|---|
| Overfitting to 101 eval cases | Notes in docs emphasize offline evaluation limits; no production claims |
| Knowledge records too synthetic or narrow | Keep adaptation methodology documented; follow Phase 7 data strategy |
| Doc type labels too coarse still | Add doc-level golden labels as optional enhancement layer |
| Improving retrieval metrics without improving business usefulness | Per-wrong-case review ensures gaps map to real business scenarios |
| Accidentally modifying Phase 8 baseline | Phase 8 baseline reports are immutable; Phase 9 creates new comparison |
| Secret or external data contamination | Secret scan + data source review before commit |

## Validation Plan

| Stage | Validation | Notes |
|---|---|---|
| Planning-only (current batch) | `openspec validate add-evaluation-driven-knowledge-coverage --strict` | Scoped to this change only |
| Implementation (knowledge + eval schema) | `./scripts/run_quality_gate.sh` | Level 4 — data, retrieval, evaluation |
| Pre-archive / pre-push | `./scripts/run_quality_gate.sh` + `openspec validate --all` | Integration 0 skip, coverage ≥70% |
