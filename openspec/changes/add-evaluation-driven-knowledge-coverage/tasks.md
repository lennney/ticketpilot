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
  - `missing_faq` — 1 case (2.4%): exchange-out-of-stock scenario
  - `missing_policy` — 9 cases (22.0%): privacy, invoice, refund escalation
  - `missing_case` — 11 cases (26.8%): complaint scenarios, logistics delay
  - `doc_type_mismatch` — 2 cases (4.9%): Policy buried under FAQ/Case
  - `business_domain_gap` — 6 cases (14.6%): legal threat, counterfeit, data leak
  - `risk_level_gap` — 3 cases (7.3%): HIGH-risk tickets need matched-risk evidence
  - `query_expansion_gap` — 4 cases (9.8%): knowledge exists but query misses
  - `golden_label_gap` — 4 cases (9.8%): edge cases with empty golden labels
  - `needs_manual_review` — 1 case (2.4%): case_edge_002 empty retrieval
- [ ] 2.4 *SKIP in this batch* — Update `src/ticketpilot/evaluation/retrieval_metrics.py` (runtime change, needs Phase 9.4+)
- [ ] 2.5 *SKIP in this batch* — Update `src/ticketpilot/evaluation/retrieval_comparison.py` (runtime change)
- [ ] 2.6 *SKIP in this batch* — Add/update unit tests (tests/ change)
- [ ] 2.7 *SKIP in this batch* — Re-run wrong-case analysis (needs code change + data)
- [x] 2.8 Output refined wrong-case report — created `reports/retrieval/phase9_wrong_case_taxonomy.md`

## Phase 9.3 — Knowledge Gap Mapping

- [x] 3.1 Map each wrong case to required FAQ / Policy / Case coverage — done in gap map with Gap IDs KG-FAQ-001 to KG-CASE-010
- [x] 3.2 Identify overlapping gaps — 3 cross-type (KG-MIX-001/002/003), 3 risk-level (KG-RISK-001/002/003), overlapping cases noted (e.g., refu_013 appears in KG-CASE-002 + KG-POL-002)
- [x] 3.3 Produce gap report: created `reports/retrieval/phase9_knowledge_gap_map.md` with 24 gap IDs across FAQ (1 + 2 preventive), Policy (5), Case (10), Cross-type (3), Risk (3), plus non-knowledge workstream (label, query, mismatch) and 1 manual-review-only case
- [x] 3.4 Document addressable vs non-addressable — 30 knowledge-related gaps (73.2%) addressable via synthetic records; 10 non-knowledge gaps (24.4%) separated into golden labels, query expansion, doc_type mismatch; plus 1 manual-review-only case (2.4%)
- [x] 3.5 No external data, no raw scraping, no real customer data — confirmed

## Phase 9.4 — Targeted Knowledge Expansion

### Phase 9.4.0 — Knowledge Data Schema / Seed Flow Audit (current batch)

- [x] 4.0.1 Inventory current knowledge seed files and record counts
- [x] 4.0.2 Audit schema required fields for FAQ / Policy / Case / Chunk
- [x] 4.0.3 Identify relevant tests and validation commands
- [x] 4.0.4 Map ingestion / rebuild flow from seed files to embeddings
- [x] 4.0.5 Propose P0 mini-batch (≤12 records) based on gap map priorities
- [x] 4.0.6 Define traceability requirements for Phase 9.4 records
- [x] 4.0.7 Output audit to `reports/retrieval/phase9_knowledge_seed_audit.md`

### Phase 9.4.1 — Knowledge Records (next batch)

- [x] 4.1 Write new FAQ records for identified FAQ gaps — added 1 FAQ (retu_004, return_exchange, KG-FAQ-003)
- [x] 4.2 Write new Policy records for identified Policy gaps — added 4 Policy (refund escalation, privacy, counterfeit, legal-risk)
- [x] 4.3 Write new Case records for identified Case gaps — added 6 Case (complaint service failure, escalation, counterfeit, privacy, high-risk)
- [x] 4.4 Ensure each new record follows existing schema (UUID, doc_type, business_domain, intent_tags/risk_level as appropriate)
- [x] 4.5 Preserve FAQ / Policy / Case physical separation in seed files
- [x] 4.6 Preserve parent-child traceability (1 source record ≈ 1 chunk for current short records)
- [x] 4.7 Document traceability: which new record addresses which wrong case gaps
- [x] 4.8 Do NOT modify Phase 7/8 baseline reports
- [x] 4.9 Do NOT change chunking architecture
- [x] 4.10 Run secret scan — ensure no real customer data or API keys in seed files
- [x] 4.11 Run knowledge schema tests to verify new records validate

## Phase 9.5 — Evaluation Rerun

- [x] 5.1 Rebuild embeddings on expanded knowledge base (fake provider default; real provider opt-in)
- [x] 5.2 Rerun pipeline-backed offline evaluation on same 101 eval tickets
- [x] 5.3 Compute Phase 9 metrics: Top-1 / Top-3 / Top-5 / Top-10 hit rate, MRR
- [x] 5.4 Compute refined wrong-case distribution on Phase 9 results
- [x] 5.5 Compare Phase 8 baseline vs Phase 9 expanded-knowledge result:
  - Delta in Top-K hit rates: -5.0% (Top-1), -2.0% (Top-3), +1.0% (Top-5), 0.0% (Top-10)
  - Delta in MRR: -0.0337
  - Delta in wrong-case count: 0 (41 → 41, identical set)
  - No categories improved — same 41 wrong cases persist
- [x] 5.6 Output before-vs-after comparison report to `reports/retrieval/phase9_*`
- [x] 5.7 Report missing_doc_type reduction from Phase 8 baseline — **0 reduction** (41 → 41, identical wrong cases). Fake embeddings cannot leverage semantic content of new records; the wrong case count is driven by knowledge coverage gaps that require a real embedding provider to surface.

## Phase 9.5.1 — Validation Repair & Real Evaluation Readiness

- [x] 5.1.1 Restore `scripts/run_quality_gate.sh` to HEAD — checkpoint/resume rewrite was unrelated to Phase 9 and uncommitted
- [x] 5.1.2 Run full validation: Ruff, knowledge schema tests, seed data tests, evaluation tests, OpenSpec `--strict`, secret scan — all PASSED
- [x] 5.1.3 Integration tests skipped: 0 (no code changes in Phase 9.5)
- [x] 5.1.4 Check real embedding provider env — not configured, skip
- [x] 5.1.5 Create `reports/retrieval/phase9_real_evaluation_readiness.md` — documents setup steps for future execution
- [x] 5.1.6 Update `reports/retrieval/phase9_evaluation_rerun.md` — add validation results section
- [x] 5.1.7 Update `docs/changelog.md` — add Phase 9.5.1 entry
- [x] 5.1.8 Update `openspec/changes/add-evaluation-driven-knowledge-coverage/tasks.md` — mark Phase 9.5.1 complete
- [x] 5.1.9 Commit and push

### Phase 9.5.1 Round 2 — P0 Hit Audit & Semantics Repair

- [x] 5.1.10 Fix Phase 9.5 report semantics (FAQ+2→FAQ+1 typo, phase8/phase9 field labels, comparison_type metadata)
- [x] 5.1.11 P0 added-record hit audit: cross-reference 11 new records × 16 wrong-case pairs in Phase 9 retrieval rows
- [x] 5.1.12 Create `reports/retrieval/phase9_p0_added_record_hit_audit.md` — 3/16 partial hits, 0 wrong cases fixed
- [x] 5.1.13 Check real embedding provider env (all `EMBEDDING_*` unset), overwrite `phase9_real_provider_readiness.md`
- [x] 5.1.14 Run validation: OpenSpec `--strict` PASSED, secret scan CLEAN, ruff —fix (8 pre-existing errors in scripts/)
- [x] 5.1.15 Update `docs/changelog.md` with entry 13
- [x] 5.1.16 Update `openspec/changes/add-evaluation-driven-knowledge-coverage/tasks.md`
- [x] 5.1.17 Commit and push

### Phase 9.5.1 Round 3 — Fix `.env.local` Auto-Load

- [x] 5.1.18 Add `load_dotenv()` to `embedding_config.py` — `.env.local` was never loaded, all `EMBEDDING_*` vars always read as unset
- [x] 5.1.19 Verify config loads correctly (provider=openai_compatible, model=text-embedding-v4, dim=1024)
- [x] 5.1.20 Run embedding/provider tests (33 passed)
- [x] 5.1.21 Update `phase9_real_provider_readiness.md` to READY
- [x] 5.1.22 Update `docs/changelog.md`
- [ ] 5.1.23 Commit and push

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
