# Documentation Package Specification

## ADDED Requirements

### Requirement: Development Trace Directory

The system SHALL contain a `docs/development_trace/` directory with stage-by-stage narratives for each of the 6 archived OpenSpec changes.

#### Scenario: Development trace index exists
- **WHEN** the docs/development_trace/ directory is inspected
- **THEN** it contains an index.md and timeline.md

#### Scenario: Each archived change has a trace document
- **WHEN** inspecting docs/development_trace/
- **THEN** there is one document per archived OpenSpec change

#### Scenario: Each stage document includes required sections
- **WHEN** a stage document is inspected
- **THEN** it includes: stage goal, business problem, key design decisions, implementation scope, forbidden scope, tests and quality gate result, major risks, deferred items, related commits, and reusable patterns

#### Scenario: Documents derive from project artifacts, not aspiration
- **WHEN** a development trace document makes a factual claim
- **THEN** the claim is traceable to git log, changelog.md, phase_status.md, technical_decisions.md, or an archived OpenSpec change

### Requirement: Technical Documentation Directory

The system SHALL contain a `docs/technical/` directory with architecture, workflow, data contracts, and testing strategy reference.

#### Scenario: Technical docs reflect current implementation
- **WHEN** a technical doc describes a system parameter or behavior
- **THEN** it matches the current implementation, not a planned or aspirational design

#### Scenario: Fake embeddings are labeled as non-semantic
- **WHEN** a technical doc mentions fake embeddings
- **THEN** it labels them as "PIPELINE VERIFICATION ONLY — no semantic meaning"

#### Scenario: Quality gate doc documents all stages
- **WHEN** quality_gate.md is inspected
- **THEN** it documents Ruff, unit tests, integration tests with skip-count guard, OpenSpec validation, and secret scan stages with thresholds

### Requirement: Reusable Skills Directory

The system SHALL contain a `docs/skills/` directory with methodology documents extracted from the development process.

#### Scenario: Each skill has required template sections
- **WHEN** a skill document is inspected
- **THEN** it includes: when to use, required inputs, allowed scope, forbidden scope, procedure, acceptance checklist, common failure modes, and a reusable Claude Code prompt template

#### Scenario: Skills are generalizable
- **WHEN** a skill document specifies a requirement
- **THEN** it does not reference TicketPilot-specific implementation details as mandatory

### Requirement: Prompt Library

The system SHALL contain a `docs/prompts/` directory with role-based prompts for each agent type used in the project.

#### Scenario: Prompt directory exists
- **WHEN** the docs/prompts/ directory is inspected
- **THEN** it contains prompts for project-director, system-architect, qa-evaluator, phase-supervisor, and batch implementation agents

### Requirement: Portfolio Documentation

The system SHALL contain a `docs/portfolio/` directory with case studies, interview materials, and a demo script.

#### Scenario: Portfolio has case studies in both languages
- **WHEN** inspecting docs/portfolio/
- **THEN** there is a project case study in Chinese and in English

#### Scenario: Portfolio distinguishes maturity levels
- **WHEN** a portfolio document describes system capabilities
- **THEN** it clearly distinguishes Demo, MVP, and production readiness

#### Scenario: Portfolio does not exaggerate
- **WHEN** a portfolio document is reviewed
- **THEN** it does not contain claims that exceed the documented implementation state

#### Scenario: Limitations document lists all deferred items
- **WHEN** limitations_and_next_steps.md is inspected
- **THEN** it lists evaluation pipeline, realistic data pack, real embedding provider, real LLM provider, trace persistence, LangGraph workflow, and production deployment as deferred

### Requirement: Truth in Documentation

All documentation SHALL use actual test counts, actual commit SHAs, and explicitly acknowledge current limitations.

#### Scenario: Test counts are actual numbers
- **WHEN** a document references test counts
- **THEN** they are exact numbers from quality gate output, not ranges or estimates

#### Scenario: Commit references use SHAs
- **WHEN** a document references a commit
- **THEN** it uses the actual commit SHA, not vague terms like "recent" or "latest"

#### Scenario: Limitations are acknowledged
- **WHEN** a document describes system capabilities
- **THEN** it acknowledges that seed data is non-realistic, fake embeddings have no semantic meaning, no auto-send exists, and human review is required for risky/unsupported outputs

#### Scenario: No invented results
- **WHEN** a document makes a factual claim
- **THEN** the claim is supported by the project's actual code, tests, or configuration

## TEST STRATEGY

### Verification (manual review)
- Each document references accurate test counts from quality gate output
- No exaggerated claims about production readiness
- All deferred items from R5.3 are listed
- Fake embedding and seed data limitations are called out wherever relevant
- Automated: `openspec validate --all` must pass after archive

### What NOT to Test
- No Python code to test (documentation-only change)
- No integration tests
- No unit tests
- No coverage threshold changes
