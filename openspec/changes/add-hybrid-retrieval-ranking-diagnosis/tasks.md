# Tasks: Hybrid Retrieval Ranking Diagnosis (Phase 10)

## Phase 10.1 — Planning (current batch)

- [x] 1.1 Create `proposal.md` — problem, goal, non-goals, scope, success criteria, risks, validation plan
- [x] 1.2 Create `design.md` — architecture constraints, trace review, bottleneck taxonomy, safety constraints
- [x] 1.3 Create `tasks.md` — this file
- [x] 1.4 Create `specs/retrieval-evaluation/spec.md` — bottleneck taxonomy spec delta, layered trace export, recommendation report requirements
- [x] 1.5 Create `specs/retrieval-trace/spec.md` — trace field gap analysis, provider-aware export, disclaimer requirements
- [ ] 1.6 Run `openspec validate add-hybrid-retrieval-ranking-diagnosis --strict`
- [ ] 1.7 Update `docs/changelog.md` with Phase 10 planning entry
- [ ] 1.8 No runtime/data changes; no forbidden file modifications

## Phase 10.2 — Trace Data Audit

- [x] 2.1 Inspect current `RetrievalTrace` fields: verify keyword/vector/fused results include chunk_id, doc_id, doc_type, score, rank
- [x] 2.2 Identify any missing trace fields needed for bottleneck classification — only gap is export serialization, not trace schema
- [x] 2.3 Verify trace captures embedding provider identity — present in both RetrievalTrace and VectorResult
- [x] 2.4 Verify trace captures RRF contributions per result — FusedResult has keyword_rank/contribution, vector_rank/contribution, sources
- [x] 2.5 Document trace field gaps in audit note — created `reports/retrieval/phase10_trace_data_audit.md`
- [x] 2.6 Key finding: RetrievalTrace at runtime already contains all data needed. Missing serialization in export script (keyword_results, vector_results, fused_results not currently exported)

## Phase 10.3 — P0 Trace Export

- [x] 3.1 Write export script that captures per-case RetrievalTrace for all P0-related cases (~14 cases)
- [x] 3.2 Export must include: keyword results (full list), vector results (full list), fused results (full list), final evidence IDs, provider identity
- [x] 3.3 Cross-reference P0 added record chunk_ids against each trace layer
- [x] 3.4 Export P0 record best-rank per case: best keyword rank, best vector rank, best fused rank (or None if absent)
- [x] 3.5 Output to `reports/retrieval/phase10_p0_layered_traces.json`
- [x] 3.6 Do not change retrieval algorithm, RRF, query builder, or embedding provider
- [x] 3.7 Use real provider for semantic ranking conclusions (OpenAICompatible, 1024-d)

## Phase 10.4 — Bottleneck Classification

- [x] 4.1 Classify each P0 case using the 8-category bottleneck taxonomy:
  - `keyword_not_recalled` — programmatic: chunk_id absent from keyword results
  - `vector_not_recalled` — programmatic: chunk_id absent from vector results
  - `recalled_but_fused_low` — programmatic: in keyword/vector but fused rank > top_k
  - `fused_top10_but_metric_still_wrong` — programmatic: in fused top_k but case still wrong
  - `doc_level_label_missing` — programmatic: golden.expected_relevant_doc_ids is empty
  - `query_expansion_gap` — manual: query underspecified for existing knowledge
  - `empty_retrieval` — programmatic: both retrievers return empty
  - `provider_identity_issue` — programmatic: trace provider differs from expected
- [x] 4.2 Produce `reports/retrieval/phase10_p0_bottleneck_classification.md` with per-case bottleneck and evidence
- [x] 4.3 Include recommendation for each case: doc_level_label / query_expansion / rrf_tuning / reranker / limitation
- [x] 4.4 No changes to golden labels, retrieval code, or knowledge base

## Phase 10.5 — Recommendation Report

- [ ] 5.1 Aggregate bottleneck distribution: count per category across P0 cases
- [ ] 5.2 Determine dominant bottleneck(s)
- [ ] 5.3 Produce recommendation: which next step(s) would have the highest impact
  - Add doc-level golden labels
  - Adjust query expansion
  - Tune RRF k or fusion approach
  - Add reranker
  - Accept remaining wrong cases as limitation
- [ ] 5.4 Output to `reports/retrieval/phase10_recommendation.md` (or integrated into diagnosis report)

## Phase 10.6 — Portfolio Delta

- [ ] 6.1 Create compact portfolio snapshot summarizing Phase 10 findings
- [ ] 6.2 Include: bottleneck distribution, P0 rank tracking summary, recommendation
- [ ] 6.3 Update portfolio product case onepager if needed (Phase 10 status)
- [ ] 6.4 No changes to Phase 7/8/9 portfolio docs

## Phase 10.7 — Final Validation and Archive

- [ ] 7.1 Run full quality gate: unit tests + integration tests + coverage + ruff + secret scan
- [ ] 7.2 Verify integration tests: 0 skipped
- [ ] 7.3 Run `openspec validate add-hybrid-retrieval-ranking-diagnosis --strict`
- [ ] 7.4 Run `openspec validate --all`
- [ ] 7.5 Verify no Phase 7/8/9 baseline reports modified
- [ ] 7.6 Archive change
- [ ] 7.7 Commit and push
