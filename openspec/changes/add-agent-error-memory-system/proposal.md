# Proposal: Agent Error Memory and Repair Learning System

## Why

Over 12 phases, the AI Development Harness encountered repeated error patterns: integration test skips going undetected, OpenSpec validation failures, GBK encoding issues, stale export files, AttributeError on None.strip(), and more. Without a durable memory system, each batch risks repeating the same mistakes.

This proposal adds a persistent error-learning layer to the harness.

## What Changes

1. OpenSpec change `add-agent-error-memory-system/` with spec for error memory schema
2. `reports/harness/error_memory.jsonl` — structured error log with learning entries
3. `reports/harness/repair_playbook.md` — categorized repair procedures
4. `docs/harness/agent_learning_rules.md` — rules to read before every harness batch
5. `docs/harness/preflight_checklist.md` — pre-batch verification steps
6. `prompts/harness/post_failure_reflection.md` — reflection template after failures
7. `prompts/harness/memory_audit.md` — periodic audit of error memory
8. `AGENTS.md` — minimal update with learning system reference

## Non-Goals

- Runtime product features
- Retrieval tuning
- Embedding changes
- Golden label modification
- Archived report modification
- Real LLM API integration
- Full chat transcript storage

## Scope Boundaries

- Harness/process improvement only
- No product runtime changes
- No retrieval/RRF/embeddings/chunking changes
- No knowledge/golden label changes
- No archived report modifications
- No secrets in error memory
- No full chat transcript storage
- No private or emotional conversation content

## Privacy Constraints

- Error memory contains: error type, symptom, root cause, failed command, repair action, prevention rule, commit hash, related files
- Error memory does NOT contain: API keys, tokens, Authorization headers, full chat transcripts, private personal content, raw provider responses
- Entries are concise and audit-friendly
- Backfill only from verified existing logs