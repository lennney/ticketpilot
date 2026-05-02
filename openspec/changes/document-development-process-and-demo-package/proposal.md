# Proposal: Document Development Process and Demo Package

## Problem

TicketPilot has completed 6 OpenSpec changes across ~30 commits, but the
development process, architecture decisions, and reusable patterns are
captured only in git history and internal docs. This creates several risks:

1. **Knowledge loss**: The spec-driven, batch-based development methodology
   is undocumented. New contributors (or Claude Code in a fresh session)
   cannot replicate it without reading every archived change.
2. **No demo package**: The project is interview-presentable but has no
   structured demo script, talking points, or case study narrative.
3. **No reusable skills**: The 6 implemented changes encode reusable patterns
   (hybrid retrieval, evidence-grounded generation, human review workflow)
   that could accelerate future projects but are locked inside TicketPilot.
4. **No portfolio asset**: A well-documented project case study is valuable
   for interviews and team onboarding.

## Scope

Documentation-only. No source code, no tests, no new features, no runtime
behavior changes.

## Deliverables

1. **Development trace** (`docs/development_trace/`): Stage-by-stage narrative
   of all 6 implemented changes, including goals, decisions, risks, and commits.
2. **Technical docs** (`docs/technical/`): Architecture, workflow, data contracts,
   testing strategy, and deferred items reference.
3. **Reusable skills** (`docs/skills/`): Codified development methodologies
   extracted from the 6 changes, each with procedure, checklist, and prompt.
4. **Prompt library** (`docs/prompts/`): Role-based and batch prompts for
   each agent type used in the project.
5. **Portfolio docs** (`docs/portfolio/`): Case study (CN/EN), interview talking
   points, demo script, and limitations statement.

## Non-Goals

- Modifying any source code, tests, or runtime behavior
- Adding evaluation pipeline (deferred)
- Adding realistic data pack (deferred)
- Adding real embedding or LLM provider (deferred)
- Adding LangGraph, Langfuse, Ragas, or production deployment
