# Tasks: Evaluation-driven Knowledge Coverage Optimization (Phase 9)

## Phase 9.1 — Planning (current batch)

- [x] 1.1 Create `proposal.md` — problem, goal, non-goals, scope, success criteria, risks, validation plan
- [x] 1.2 Create `design.md` — architecture constraints, data flow, taxonomy design, safety constraints
- [x] 1.3 Create `tasks.md` — this file
- [x] 1.4 Create `specs/retrieval-evaluation/spec.md` — refined wrong-case taxonomy, doc-level golden labels, Phase-9 comparison requirements
- [x] 1.5 Create `specs/knowledge-schema/spec.md` — knowledge expansion traceability, seed data rules
- [x] 1.6 Run `openspec validate add-evaluation-driven-knowledge-coverage --strict`
- [x] 1.7 Update `docs/changelog.md` with Phase 9 planning entry
- [x] 1.8 No runtime/data changes; no forbidden file modifications

## Phase 9.2 — Wrong-Case Taxonomy Refinement

- [x] 2.1 Inspect current fake vs real wrong-case reports (`reports/retrieval/wrong_cases.md`)
- [x] 2.2 Inspect per-case retrieval traces (`reports/retrieval/fake_vs_real_comparison.json`) for the 41 wrong cases
- [x] 2.3 Refine `missing_doc_type` into 8 actionable categories — done in taxonomy report:
  - `missing_faq` — 3 cases (7.3%): complaint UI/accessibility gaps
  - `missing_policy` — 8 cases (19.5%): privacy, invoice, refund escalation
  - `missing_case` — 10 cases (24.4%): complaint scenarios, logistics delay
  - `doc_type_mismatch` — 2 cases (4.9%): Policy buried under FAQ/Case
  - `business_domain_gap` — 6 cases (14.6%): legal threat, counterfeit, data leak
  - `risk_level_gap` — 4 cases (9.8%): HIGH-risk tickets need matched-risk evidence
  - `query_expansion_gap` — 3 cases (7.3%): knowledge exists but query misses
  - `golden_label_gap` — 4 cases (9.8%): edge cases with empty golden labels
  - `needs_manual_review` — 1 case (2.4%): case_edge_002 empty retrieval
- [ ] 2.4 *SKIP in this batch* — Update `src/ticketpilot/evaluation/retrieval_metrics.py` (runtime change, needs Phase 9.4+)
- [ ] 2.5 *SKIP in this batch* — Update `src/ticketpilot/evaluation/retrieval_comparison.py` (runtime change)
- [ ] 2.6 *SKIP in this batch* — Add/update unit tests (tests/ change)
- [ ] 2.7 *SKIP in this batch* — Re-run wrong-case analysis (needs code change + data)
- [x] 2.8 Output refined wrong-case report — created `reports/retrieval/phase9_wrong_case_taxonomy.md`

## Phase 9.3 — Knowledge Gap Mapping

- [ ] 3.1 Map each wrong case to required FAQ / Policy / Case coverage
- [ ] 3.2 Identify overlapping gaps (multiple cases needing same knowledge area)
- [ ] 3.3 Produce gap report: per-intent gap summary, per-domain gap summary, prioritized expansion list
- [ ] 3.4 Document which gaps are addressable via synthetic/adapted records and which are inherently out-of-scope
- [ ] 3.5 No external data, no raw scraping, no real customer data

## Phase 9.4 — Targeted Knowledge Expansion

- [ ] 4.1 Write new FAQ records for identified FAQ gaps
- [ ] 4.2 Write new Policy records for identified Policy gaps
- [ ] 4.3 Write new Case records for identified Case gaps
- [ ] 4.4 Ensure each new record follows existing schema (UUID, doc_type, business_domain, intent_tags/risk_level as appropriate)
- [ ] 4.5 Preserve FAQ / Policy / Case physical separation in seed files
- [ ] 4.6 Preserve parent-child traceability (1 source record ≈ 1 chunk for current short records)
- [ ] 4.7 Document traceability: which new record addresses which wrong case gaps
- [ ] 4.8 Do NOT modify Phase 7/8 baseline reports
- [ ] 4.9 Do NOT change chunking architecture
- [ ] 4.10 Run secret scan — ensure no real customer data or API keys in seed files
- [ ] 4.11 Run knowledge schema tests to verify new records validate

## Phase 9.5 — Evaluation Rerun

- [ ] 5.1 Rebuild embeddings on expanded knowledge base (fake provider default; real provider opt-in)
- [ ] 5.2 Rerun pipeline-backed offline evaluation on same 101 eval tickets
- [ ] 5.3 Compute Phase 9 metrics: Top-1 / Top-3 / Top-5 / Top-10 hit rate, MRR
- [ ] 5.4 Compute refined wrong-case distribution on Phase 9 results
- [ ] 5.5 Compare Phase 8 baseline vs Phase 9 expanded-knowledge result:
  - Delta in Top-K hit rates
  - Delta in MRR
  - Delta in wrong-case count and category distribution
  - Which categories improved, which persist
- [ ] 5.6 Output before-vs-after comparison report to `reports/retrieval/phase9_*`
- [ ] 5.7 Report missing_doc_type reduction from Phase 8 baseline (41)

## Phase 9.6 — Portfolio Summary

- [ ] 6.1 Create Phase 9 portfolio snapshot (`docs/portfolio/phase9_knowledge_coverage_snapshot.md`)
- [ ] 6.2 Document product-manager interpretation:
  - "Not blindly changing models — using evaluation to identify and close knowledge coverage gaps"
- [ ] 6.3 Include before-vs-after metrics, refined taxonomy, and gap coverage summary
- [ ] 6.4 Update `docs/portfolio/ticketpilot_product_case_onepager.md` — Phase 9 status
- [ ] 6.5 Add resume bullets and interview talking points

## Phase 9.7 — Final Validation and Archive

- [ ] 7.1 Run `openspec validate add-evaluation-driven-knowledge-coverage --strict`
- [ ] 7.2 Run `openspec validate --all`
- [ ] 7.3 Run full quality gate: `bash scripts/run_quality_gate.sh`
- [ ] 7.4 Verify 0 skipped integration tests
- [ ] 7.5 Verify coverage ≥70%
- [ ] 7.6 Secret scan clean
- [ ] 7.7 Archive change: `openspec archive add-evaluation-driven-knowledge-coverage`
- [ ] 7.8 Git commit and push
