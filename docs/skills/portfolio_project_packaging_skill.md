# Portfolio Project Packaging Skill

## Purpose

Convert a completed project into portfolio-ready documentation for job applications, technical interviews, and demonstrations. This covers creating development trace documents (historical narrative of how the project evolved), technical reference documentation, portfolio case studies (English and Chinese), a demo script, and interview talking points. Every document must be honest about limitations and avoid exaggerated claims.

## When to Use

- Preparing a project for portfolio or job application use
- Creating case studies for interviews (system design, product management, engineering)
- Building a demo script for live demonstrations
- Documenting a project's development history for future reference
- Creating bilingual (Chinese/English) project documentation
- Do NOT use this to create marketing materials that exaggerate capabilities

## Required Inputs

- Git commit history (`git log --oneline`) for chronological narrative
- Changelog (`docs/changelog.md`) for batch-level change summaries
- Phase status (`docs/phase_status.md`) for acceptance status
- Technical decisions (`docs/technical_decisions.md`) for architecture rationale
- Source code documentation (docstrings, module docs)
- Test results and quality gate outputs (exact test counts, coverage numbers)
- OpenSpec change directories for design context

## Allowed Scope

- Creating development trace documents (stage-by-stage narrative with design decisions, implementation scope, test results, risks, deferred items, reusable patterns)
- Creating technical reference documentation (architecture, pipeline, data contracts, testing strategy, quality gate, glossary)
- Creating portfolio case studies (Chinese and English) for interviews
- Creating a demo script with step-by-step instructions and sample inputs
- Creating interview talking points (30-second, 1-minute, 3-minute pitches)
- Creating a limitations document clearly distinguishing demo / MVP / production readiness

## Forbidden Scope

- Do NOT claim production readiness
- Do NOT claim real semantic retrieval quality from fake embeddings
- Do NOT claim real enterprise data coverage from seed data
- Do NOT claim auto-send exists
- Do NOT claim real LLM provider exists
- Do NOT claim evaluation pipeline exists
- Do NOT use exaggerated or aspirational language ("enterprise-grade," "production-proven," "battle-tested")
- Do NOT omit known limitations or deferred items
- Do NOT fabricate test counts, commit SHAs, or performance metrics
- Do NOT claim the system is more mature than documented in acceptance status

## Step-by-Step Procedure

1. **Gather source materials**
   - Run `git log --oneline` for the full commit history
   - Read `docs/changelog.md` for batched change summaries
   - Read `docs/phase_status.md` for acceptance status
   - Read `docs/technical_decisions.md` for architecture decisions
   - Read OpenSpec change directories (proposal, design, spec, tasks)
   - Collect exact test counts and coverage numbers from quality gate runs

2. **Create development trace documents** (docs/development_trace/)
   - Create an index.md with project overview, readiness levels, stage overview, key constraints, and cross-stage deferred items
   - Create a timeline.md with chronological commit history organized by date and stage
   - For each OpenSpec change, create a stage document with:
     - Stage goal and business problem
     - Key design decisions with rationale (and alternatives considered)
     - Implementation scope (what was built, what was explicitly excluded)
     - Forbidden scope (what was deferred or ruled out)
     - Tests and quality gate result at completion (exact counts)
     - Major risks and mitigations
     - Deferred items
     - Related commits (ordered, with commit SHAs and messages)
     - Reusable patterns extracted from the stage

3. **Create technical reference documentation** (docs/technical/)
   - System architecture: overall context, stage diagram, data flow, product boundary (what it does and does not do)
   - Workflow pipeline: pipeline stages, input/output types, orchestration, integrity guarantees
   - Data contracts: all Pydantic models with field descriptions, input/output boundaries
   - Risk assessment rules: all 8 risk flags (6 substantive + 2 meta), severity calculation, must_human_review behavior
   - Retrieval architecture: source separation, chunking, hybrid retrieval, fake embedding limitation
   - Evidence draft generation: DraftReply, provider strategy, CitationValidator, safe fallbacks, no auto-send
   - Human review console: Streamlit MVP, ReviewStore JSONL, approve/edit/escalate/reject, audit trail, no auto-send
   - Quality gate: stages, thresholds, current results, design principles
   - Testing strategy: unit vs integration test boundaries, mocking strategy, golden cases, fake provider testing boundaries
   - Open questions and deferred items: all known gaps and future work
   - Glossary: Chinese-English term mapping and definitions

4. **Create portfolio documentation** (docs/portfolio/)
   - Case study in English: tech stack, architecture, development process, results, limitations
   - Case study in Chinese: same content as English for bilingual portfolio
   - Interview talking points: 30/60/180-second pitches, PM/engineering/risk angles, anticipated Q&A
   - Demo script: step-by-step flow with sample inputs, expected outputs, what-not-to-claim
   - Limitations document: demo vs MVP vs production readiness, comprehensive deferred items

5. **Apply truth-in-documentation rules to every document**
   - Fake embeddings → "PIPELINE VERIFICATION ONLY — no semantic meaning"
   - Seed data → synthetic, not real enterprise data
   - No auto-send → documented as architectural constraint, not missing feature
   - High-risk / unsupported / no-evidence → requires human review
   - Real LLM → not implemented (FakeDraftProvider only)
   - Evaluation pipeline → deferred, not implemented
   - All deferred items listed per the comprehensive list

6. **Create skill documentation** (docs/skills/)
   - Extract reusable methodologies from the development process
   - Each skill: purpose, when to use, required inputs, allowed/forbidden scope, step-by-step procedure, acceptance checklist, common failure modes, reusable Claude Code prompt template, TicketPilot example
   - See individual skill documents for specifics

## Acceptance Checklist

- [ ] Development trace index.md and timeline.md exist
- [ ] One development trace document per archived OpenSpec change
- [ ] Each trace doc includes: goal, design decisions, scope, forbidden scope, tests, risks, deferred, commits, patterns
- [ ] Technical docs cover: architecture, pipeline, data contracts, risk rules, retrieval, drafting, review, quality gate, testing, glossary, open questions
- [ ] Portfolio docs include: case study EN, case study CN, interview talking points, demo script, limitations
- [ ] Skills docs exist for all extracted methodologies
- [ ] Fake embeddings labeled as pipeline verification only wherever mentioned
- [ ] Seed data labeled as synthetic
- [ ] No auto-send documented as constraint
- [ ] Human review required for risky/unsupported outputs
- [ ] All deferred items listed
- [ ] Test counts are exact numbers (not ranges)
- [ ] Commit references use SHAs (not "recent," "latest")
- [ ] No exaggerated claims about production readiness

## Common Failure Modes

- **Claiming more than the system delivers**: "Retrieval quality is verified by integration tests" is misleading if the tests use fake embeddings. Say "Pipeline mechanics are verified; real retrieval quality is not measured."
- **Omitting the fake embedding label**: The most common documentation error. Every document that mentions retrieval or embeddings must include the limitation label.
- **Using aspirational language**: "Will scale to production" is speculation. "Not designed for production" is honest. Use present-tense, verifiable descriptions.
- **Rounding test counts**: "About 300 unit tests" when the exact count is 325. Use exact numbers from the quality gate output.
- **Vague commit references**: "Recently fixed" vs "commit a1b2c3d." Always use SHAs.
- **Inconsistent deferred items list**: If the limitations doc says 10 deferred items but a technical doc only lists 5, the documentation is inconsistent. Maintain a single source of truth.
- **Not distinguishing demo, MVP, and production readiness**: These are different maturity levels. A system can be demo-ready but not MVP-ready. Be explicit about each.

## Reusable Claude Code Prompt Template

```
I need to package this project for portfolio documentation. Use the following process:

1. **Gather**: git log --oneline, changelog.md, phase_status.md, technical_decisions.md, OpenSpec changes, quality gate results

2. **Development trace** (docs/development_trace/):
   - index.md: project overview, stages, constraints, deferred items
   - timeline.md: chronological commits by date and stage
   - One doc per archived change: goal, decisions, scope, forbidden scope, tests, risks, deferred, commits, patterns

3. **Technical docs** (docs/technical/):
   - Architecture, pipeline, data contracts, risk rules, retrieval, drafting, review, quality gate, testing, glossary, open questions

4. **Portfolio docs** (docs/portfolio/):
   - Case study (EN + CN), interview talking points, demo script, limitations

5. **Skills docs** (docs/skills/):
   - Reusable methodologies: purpose, usage, inputs, scope, procedure, checklist, failure modes, prompt template, example

Truth rules (apply to every document):
- [ ] Fake embeddings = pipeline verification only, no semantic meaning
- [ ] Seed data = synthetic, not real enterprise data
- [ ] No auto-send = architectural constraint
- [ ] High-risk/unsupported = human review required
- [ ] Real LLM = not implemented
- [ ] Evaluation pipeline = deferred
- [ ] Test counts = exact, from quality gate
- [ ] Commits = SHA references, not vague terms
- [ ] No exaggerated claims
```

## TicketPilot Example

TicketPilot's documentation was packaged in 4 phases:

**Phase 1 (Batch 1) -- Development Trace**: 9 documents covering all 6 archived OpenSpec changes plus index and timeline. Each document includes goal, design decisions, implementation scope, forbidden scope, test results, risks, deferred items, commits with SHAs, and reusable patterns.

**Phase 2 (Batch 2A) -- Technical Docs**: 11 documents covering system architecture, workflow pipeline, data contracts, risk assessment rules, retrieval architecture, evidence draft generation, human review console, quality gate, testing strategy, open questions, and glossary.

**Phase 2B (Batch 2B) -- Portfolio Docs**: 5 documents including Chinese and English case studies, interview talking points, demo script, and limitations. All fake embedding limitations and deferred items clearly documented. Demo script includes explicit "what not to claim" section.

**Phase 3 (Batch 3A) -- Skills Docs** (this batch): 10 reusable skill documents extracted from the TicketPilot development process, each with a TicketPilot example demonstrating the skill in practice.

**Content constraints enforced in every document**:
- Fake embeddings = "PIPELINE VERIFICATION ONLY -- no semantic meaning"
- Seed data = 36 synthetic documents, not real enterprise data
- No auto-send = documented architectural constraint
- High-risk/unsupported = requires human review
- Evaluation pipeline, real data pack, real embedding provider, real LLM provider, trace persistence, LangGraph workflow, production deployment = listed as deferred
