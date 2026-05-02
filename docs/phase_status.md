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