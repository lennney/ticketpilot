# TicketPilot Phase Status

## Stage 1A - Ticket Intake + Risk Triage

Status: ACCEPTED

Summary:
- Ticket normalization implemented
- Intent classification implemented
- Risk assessment implemented
- Unit tests passed
- Acceptance and QA reports created

## Stage 1B Batch 1 - Knowledge Layer + Chunking

Status: ACCEPTED

Summary:
- FAQ / Policy / Case seed data physically separated
- Parent-child chunking implemented
- Child-parent traceability tested
- Seed data validation passed

## Stage 1B Batch 2 - Hybrid Retrieval Engine

Status: ACCEPTED

Summary:
- Fake embedding provider implemented
- Keyword retrieval implemented
- Vector retrieval implemented
- RRF implemented
- Retrieval traces implemented
- Unit tests passed
- Integration tests pass (55 passed, 0 skipped) — DB verification gap closed

## Stage 1C — Evidence-Grounded Draft Generation

Status: ACCEPTED

Summary:
- Citation, DraftReply, DraftGenerationTrace Pydantic schemas defined
- AbstractDraftProvider interface + deterministic FakeDraftProvider implemented
- CitationValidator for unsupported claim detection implemented
- `generate_draft(ticket_output)` standalone composition function implemented
- `run_pipeline_with_draft(raw_ticket)` optional workflow entrypoint implemented
- DraftedTicketResult wrapper schema combines TicketOutput + DraftReply
- No-evidence fallback: safe Chinese message without deterministic policy promises
- High-risk and unsupported-claim paths preserve must_human_review=true
- No modifications to pipeline.py, schema/ticket.py, or existing modules
- Unit tests: 263 passed (203 prior + 60 new drafting-specific tests)
- Integration tests: 65 passed (55 prior + 10 new drafting-specific)
- 0 skipped integration tests
- No real LLM, no network, no API keys, no env dependencies
- Full quality gate passed
- OpenSpec change archived

## Stage 1D — Human Review Console

Status: ACCEPTED

Summary:
- ReviewAction enum (APPROVE, EDIT, ESCALATE, REJECT) defined
- ReviewDecision Pydantic model with full audit trail (15+ fields)
- ReviewStore append-only JSONL persistence with save/load_all/count
- review_trigger_reasons captures why human review was needed (high_risk, no_evidence, unsupported_claims, generation_error)
- Streamlit console MVP for human review workflow
- Console supports RawTicket input, full pipeline display, action buttons, and JSONL persistence
- Console explicitly disclaims no auto-send ("审核控制台 — 不自动发送回复")
- Pure helper functions (determine_trigger_reasons, build_review_decision) with 40 unit tests
- Integration tests for console module imports, ReviewDecision persistence, and no-auto-send verification
- Unit tests: 325 passed (285 prior + 40 new)
- Integration tests: 74 passed (65 prior + 9 new)
- 0 skipped integration tests
- No modifications to pipeline.py, drafting, retrieval, risk, intake, classification, or database code
- Full quality gate passed
- OpenSpec change ready for archive

## Documentation Package (document-development-process-and-demo-package)

Status: ACCEPTED

Summary:
- Development trace (`docs/development_trace/`): 9 files — index, timeline, and 7 stage narratives covering all 6 archived OpenSpec changes plus quality gate hardening
- Technical docs (`docs/technical/`): 11 files — system architecture, workflow pipeline, data contracts, risk assessment rules, retrieval architecture, evidence draft generation, human review console, quality gate, testing strategy, open questions, glossary
- Reusable skills (`docs/skills/`): 10 files — spec-driven development, batch implementation, quality gate acceptance, OpenSpec archive, product boundary, retrieval evaluation, evidence-grounded generation, human review workflow, secure AI development, portfolio packaging
- Prompt library (`docs/prompts/`): 7 files — project director, system architect, QA evaluator, phase supervisor, Claude Code batch, acceptance review, archive prompts
- Portfolio docs (`docs/portfolio/`): 5 files — Chinese case study, English case study, interview talking points, demo script, limitations and next steps
- All documents consistently state:
  - Current system is local demo / portfolio-ready, not production-ready
  - Fake embedding proves pipeline mechanics, not real semantic retrieval quality
  - Current knowledge base is seed data, not real enterprise data
  - No auto-send exists
  - Human review is required for risky or unsupported outputs
  - Evaluation pipeline, realistic data pack, real embedding provider, real LLM provider, trace persistence, LangGraph workflow, auth/multi-user review, production deployment, and real customer service integration are deferred
- Unit tests: 325 passed, 76.57% coverage (unchanged)
- Integration tests: 74 passed, 0 skipped (unchanged)
- No source code modified
- Full quality gate passed
- OpenSpec change archived

## Evaluation Pipeline (add-evaluation-pipeline)

Status: ACCEPTED

Summary:
- Evaluation dataset created (`data/eval/tickets_eval.csv`, `data/eval/golden_expectations.csv`) with 10 seed tickets covering 8 intent classes, 5 risk flag categories, 3 severity levels, and edge cases
- Evaluation schemas, loaders, and metrics implemented as pure deterministic functions
- CLI evaluation runner (`scripts/run_eval.py`) supports both CSV-prediction and pipeline-prediction modes
- Pipeline-backed prediction generation (`predict_from_pipeline()`) maps local TicketPilot pipeline output to EvalPrediction objects
- JSON and Markdown report generation implemented
- Unit tests: 433 passed (unchanged throughout all batches)
- Integration tests: 74 prior + 11 new = 85 passed, 0 skipped
- Coverage: 80.25%
- All evaluation is local deterministic / seed-data based — no real embedding provider, no real LLM, no network, no external APIs
- Reports explicitly state: seed data only, fake embedding limitation, no real-world performance claim
- No src/ or tests/ files modified outside the evaluation module
- Full quality gate passed
- OpenSpec change archived

## Public GitHub Package (add-public-github-package)

Status: ACCEPTED

Summary:
- README.md (Chinese, primary) and README.en.md (English, synchronized) rewritten for public portfolio presentation:
  - Sections 1-6 (Batch 1): What is TicketPilot, Why not a normal RAG demo, Core workflow, Feature overview, Architecture summary, Quick Start
  - Sections 7-10 (Batch 2): Documentation Map, Current Limitations, Roadmap, Safety Boundary / No Auto-Send
- .env.example updated to match actual code usage (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD); unused LLM/Langfuse placeholders commented out with explanation
- .gitignore updated with `.coverage` and `.coverage.*` patterns
- Demo guide (Batch 3): `docs/demo/README.md` with 3 demo lines (A: normal refund/return, B: high-risk complaint/legal/privacy, C: evaluation pipeline), `docs/demo/sample_tickets.md` with 7 ticket scenarios
- GitHub release checklist: `docs/github_release_checklist.md` with 11-section pre-publication checklist
- Public-claim audit: no overstated claims in README or demo docs
- No secrets, API keys, or credentials in committed files
- Safety constraints explicitly documented: no auto-send (architectural), fake embeddings (pipeline verification only), seed data only, no real LLM
- Unit tests: 433 passed (unchanged — no src/ or tests/ modifications)
- Integration tests: 85 passed, 0 skipped (unchanged)
- Coverage: 80.25% (unchanged)
- Full quality gate passed
- OpenSpec change archived

### All documents consistently state
- Local demo / portfolio-ready, not production-ready
- Fake embeddings prove pipeline mechanics, not real semantic retrieval quality
- Knowledge base is seed data (36 documents), not real enterprise data
- No auto-send exists (architectural constraint)
- Human review required for risky or unsupported outputs

## Agent Kernel Runtime (add-agent-kernel-runtime)

Status: ACCEPTED

Summary:
- Batch 1: Agent schemas and trace event models (AgentEvent, AgentRun, AgentTrace, etc.)
- Batch 2: Tool registry (ToolRegistry, RegisteredTool) and 5 tool wrappers
- Batch 3: Deterministic planner (DeterministicTaskPlanner), memory (WorkingMemory, EpisodicMemory), agent loop (run_agent_pipeline)
- Batch 4: Skill loader (SkillLoader, SkillDefinition) and 4 business skills (refund_request, complaint_escalation, account_issue, technical_issue)
- All agent code is LLM-free: deterministic keyword-based planning, fake draft provider, no embedding calls
- Human review routing for high-risk/unsupported/no-evidence outputs
- No auto-send capability introduced
- Unit tests: 636 passed (433 original + 203 agent kernel specific)
- Integration tests: 85 passed, 0 skipped (unchanged — agent integration tests deferred)
- Ruff clean
- No existing src/ or tests/ files modified outside the agent module
- No LLM, embedding, network, or auto-send introduced