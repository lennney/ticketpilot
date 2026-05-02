# Design: Document Development Process and Demo Package

## Document Architecture

### docs/development_trace/

Stage-by-stage narrative matching the 6 archived OpenSpec changes:

```
docs/development_trace/
  index.md                   # Overview and navigation
  timeline.md                # Chronological development timeline
  00_project_origin.md       # Project goals, tech stack, initial setup
  01_intake_risk_triage.md   # add-ticket-intake-risk-triage
  02_layered_retrieval_foundation.md  # add-layered-knowledge-retrieval-foundation
  03_connect_retrieval_to_pipeline.md # connect-retrieval-to-intake-risk-pipeline
  04_quality_gate_hardening.md        # close-project-audit-blockers
  05_evidence_draft_generation.md     # add-evidence-draft-generation
  06_human_review_console.md          # add-human-review-console
```

Each document includes:
- Stage goal and business problem
- Key design decisions with rationale
- Implementation scope (what was built, what was explicitly excluded)
- Forbidden scope (what was deferred or ruled out)
- Tests and quality gate result at completion
- Major risks and mitigations
- Deferred items
- Related commits (ordered, with messages)
- Reusable patterns extracted from the stage

### docs/technical/

Reference documentation organized by architectural layer:

| Document | Content |
|----------|---------|
| `system_architecture.md` | Overall system context, stage diagram, data flow |
| `workflow_pipeline.md` | 4-stage pipeline: intake → classify → assess risk → retrieve |
| `data_contracts.md` | All Pydantic models: RawTicket → TicketOutput → DraftReply → ReviewDecision |
| `risk_assessment_rules.md` | Risk rules, severity calculation, all 8 risk flags |
| `retrieval_architecture.md` | Hybrid retrieval (keyword + vector), RRF, chunking, traces |
| `evidence_draft_generation.md` | Optional drafting workflow, CitationValidator, provider strategy |
| `human_review_console.md` | Streamlit MVP, ReviewStore JSONL, action model, no-auto-send |
| `quality_gate.md` | Quality gate design: stages, thresholds, scripts |
| `testing_strategy.md` | Unit vs integration test boundaries, mocking, WSL considerations |
| `open_questions_and_deferred_items.md` | All known gaps and future work |
| `glossary.md` | Chinese-English term mapping and definitions |

### docs/skills/

Each skill documents a repeatable methodology extracted from the project:

| Skill | Source Change | Purpose |
|-------|---------------|---------|
| `spec_driven_development_skill.md` | All | How to use OpenSpec for constrained, traceable development |
| `batch_implementation_skill.md` | All | How to plan and execute batch-based implementation |
| `quality_gate_acceptance_skill.md` | All | How to run quality gate, interpret results, decide acceptance |
| `openspec_archive_skill.md` | All | How to archive a completed change |
| `ticketpilot_product_boundary_skill.md` | Project-wide | What is in/out of scope for TicketPilot |
| `retrieval_evaluation_skill.md` | 02, 03 | How to evaluate hybrid retrieval quality |
| `evidence_grounded_generation_skill.md` | 05 | How to build evidence-grounded draft generation |
| `human_review_workflow_skill.md` | 06 | How to design a human-in-the-loop review workflow |
| `secure_ai_development_skill.md` | All | Security practices: no auto-send, fake provider, no secrets |
| `portfolio_project_packaging_skill.md` | All | How to package this project for interviews |

Each skill template:
```markdown
## [Skill Name]

### When to use it

### Required inputs

### Allowed scope

### Forbidden scope

### Procedure
1. ...
2. ...
N. ...

### Acceptance checklist
- [ ] ...
- [ ] ...

### Common failure modes
- ...

### Reusable Claude Code prompt template
```

### docs/prompts/

Role-based and batch prompts used during development, organized for reuse.

| Document | Contents |
|----------|----------|
| `project_director_prompts.md` | Prompts for planning, scope checking, next-step decisions |
| `system_architect_prompts.md` | Prompts for architecture design and data flow decisions |
| `qa_evaluator_prompts.md` | Prompts for acceptance criteria and evaluation |
| `phase_supervisor_prompts.md` | Prompts for batch acceptance decisions |
| `claude_code_batch_prompts.md` | Implementation prompts used for each batch |
| `acceptance_review_prompts.md` | Review/audit prompts used for acceptance |
| `archive_prompts.md` | Archive and documentation prompts |

### docs/portfolio/

| Document | Purpose |
|----------|---------|
| `project_case_study_cn.md` | 中文案例：技术选型、架构、开发流程、成果 |
| `project_case_study_en.md` | English case study: tech stack, architecture, process, results |
| `interview_talking_points.md` | Key points for system design interviews |
| `demo_script.md` | Step-by-step demo: startup → process ticket → review → save |
| `limitations_and_next_steps.md` | Honest assessment of MVP gaps |

## Source Material

All documents are derived from:
- `git log` (commit history)
- `docs/changelog.md` (batch-level change summaries)
- `docs/phase_status.md` (stage acceptance status)
- `docs/technical_decisions.md` (architecture decisions)
- Archived OpenSpec changes in `openspec/changes/archive/`
- `openspec/specs/` (promoted specs)
- Source code docstrings (Pydantic models, module docs)

## Documentation Rules

1. No exaggerated claims — clearly label Demo, MVP, production readiness
2. Call out fake embeddings as PIPELINE VERIFICATION ONLY
3. Call out seed data as non-realistic
4. Call out no auto-send as a safety constraint, not a missing feature
5. Call out that human review is required for risky/unsupported outputs
6. List all known deferred items
7. Derive claims from actual project state, not aspirational plans
