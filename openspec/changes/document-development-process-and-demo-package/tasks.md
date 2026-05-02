## Phase 1: Planning + Review (current)

- [x] 1.0 Pre-Batch 1 documentation hygiene (inventory + deconflict legacy docs)
- [x] 1.1 Review design.md with project-director, system-architect, qa-evaluator, phase-supervisor
- [x] 1.2 Get design approval
- [x] 1.3 Create spec.md with detailed requirements per document

## Phase 2: Development Trace (docs/development_trace/)

- [ ] 2.1 Create `docs/development_trace/index.md` and `timeline.md`
- [ ] 2.2 Create `00_project_origin.md`
- [ ] 2.3 Create `01_intake_risk_triage.md`
- [ ] 2.4 Create `02_layered_retrieval_foundation.md`
- [ ] 2.5 Create `03_connect_retrieval_to_pipeline.md`
- [ ] 2.6 Create `04_quality_gate_hardening.md`
- [ ] 2.7 Create `05_evidence_draft_generation.md`
- [ ] 2.8 Create `06_human_review_console.md`

## Phase 3: Technical Docs (docs/technical/)

- [ ] 3.1 Create `system_architecture.md`
- [ ] 3.2 Create `workflow_pipeline.md`
- [ ] 3.3 Create `data_contracts.md`
- [ ] 3.4 Create `risk_assessment_rules.md`
- [ ] 3.5 Create `retrieval_architecture.md`
- [ ] 3.6 Create `evidence_draft_generation.md`
- [ ] 3.7 Create `human_review_console.md`
- [ ] 3.8 Create `quality_gate.md`
- [ ] 3.9 Create `testing_strategy.md`
- [ ] 3.10 Create `open_questions_and_deferred_items.md`
- [ ] 3.11 Create `glossary.md`

## Phase 4: Reusable Skills (docs/skills/)

- [ ] 4.1 Create `spec_driven_development_skill.md`
- [ ] 4.2 Create `batch_implementation_skill.md`
- [ ] 4.3 Create `quality_gate_acceptance_skill.md`
- [ ] 4.4 Create `openspec_archive_skill.md`
- [ ] 4.5 Create `ticketpilot_product_boundary_skill.md`
- [ ] 4.6 Create `retrieval_evaluation_skill.md`
- [ ] 4.7 Create `evidence_grounded_generation_skill.md`
- [ ] 4.8 Create `human_review_workflow_skill.md`
- [ ] 4.9 Create `secure_ai_development_skill.md`
- [ ] 4.10 Create `portfolio_project_packaging_skill.md`

## Phase 5: Prompt Library (docs/prompts/)

- [ ] 5.1 Create `project_director_prompts.md`
- [ ] 5.2 Create `system_architect_prompts.md`
- [ ] 5.3 Create `qa_evaluator_prompts.md`
- [ ] 5.4 Create `phase_supervisor_prompts.md`
- [ ] 5.5 Create `claude_code_batch_prompts.md`
- [ ] 5.6 Create `acceptance_review_prompts.md`
- [ ] 5.7 Create `archive_prompts.md`

## Phase 6: Portfolio Docs (docs/portfolio/)

- [ ] 6.1 Create `project_case_study_cn.md`
- [ ] 6.2 Create `project_case_study_en.md`
- [ ] 6.3 Create `interview_talking_points.md`
- [ ] 6.4 Create `demo_script.md`
- [ ] 6.5 Create `limitations_and_next_steps.md`

## Phase 7: Finalization

- [ ] 7.1 Verify all docs reference correct test counts, commits, and scope
- [ ] 7.2 Update `docs/changelog.md`
- [ ] 7.3 Update `docs/phase_status.md`
- [ ] 7.4 Run quality gate: `bash scripts/run_quality_gate.sh`
- [ ] 7.5 OpenSpec validate --all
- [ ] 7.6 OpenSpec archive
- [ ] 7.7 Final acceptance

## Batch Plan

| Batch | Phases | Description |
|-------|--------|-------------|
| **Batch 1** | Phase 1 + Phase 2 | Planning + development trace (planning docs reviewed by all 4 agents, then generate all trace docs) |
| **Batch 2** | Phase 3 + Phase 6 | Technical docs + portfolio (architecture, data contracts, testing strategy; case studies, demo script) |
| **Batch 3** | Phase 4 + Phase 5 + Phase 7 | Skills + prompts + finalization (reusable skills, prompt library, changelog, quality gate, archive) |
