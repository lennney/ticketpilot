# Engineering Log — TicketPilot

---

## 2026-05-07 — Phase 15.2: Chat Demo UI Skeleton

**Implementation**:
- Created `src/ticketpilot/chat/` module with 6 Pydantic schemas and 2 pure helper functions
- `ChatContext` supports multi-turn conversation: tracks current_order_id, current_issue_type, latest_risk_flags, latest_severity, latest_evidence_ids, latest_citation_ids, latest_guard_passed, human_review_required, handoff_reason, turn_count
- `append_message()`: pure function returning new ChatSession, increments turn_count for USER messages
- `update_context_from_message()`: reads metadata keys (detected_order_id, issue_type, risk_flags, etc.) without NLP parsing
- Streamlit app with 5 panels: chat history, context panel, risk panel, evidence panel, draft panel
- EvidenceDisplayItem: chunk_id + doc_type validation, optional title/score/content_preview

**Key Design Decisions**:
- ChatContext is NOT a summarization layer — it only stores structured metadata from pipeline output
- No NLP for order ID extraction in Phase 15.2 — natural language parsing deferred to Phase 15.3 adapter
- Once human_review_required is True, it stays True (only cleared by future reviewer action)
- Short follow-up questions ("谢谢", "好的") do not overwrite current_order_id

**Files**: src/ticketpilot/chat/{__init__,schemas,app}.py, tests/unit/test_chat_schemas.py (50 tests)

**Quality Gate**: 50 new tests pass, ruff clean, OpenSpec 26/26

---

## 2026-05-07 — Phase 15.1: Chat Support Product Re-alignment Planning

**Problem**: Recent iterations (Phase 13-14) drifted toward guard taxonomy internal engineering details. Product narrative was "工单分诊 + guard architecture" rather than the original vision: AI customer service copilot (e-commerce scenario).

**Solution**: Created `align-chat-support-product-experience` OpenSpec change to realign product direction.

**New Product Narrative**:
- Before: 工单分诊 + guard architecture + evidence draft backend
- After: 面向中文电商的 AI 客服 Copilot — 前台聊天体验 + 后台人工审核台

**Key Design Decisions**:
- Chat demo uses Streamlit (not React/Next.js) — MVP simplicity
- Pipeline output adapted via `ticket_output_to_chat_display()` — no pipeline changes needed
- Guard taxonomy remains as safety foundation but is not the product narrative
- Risk decision matrix: severity × evidence × guard → human_review_required
- No auto-send: all drafts are demo display only
- Existing review console reused as human reviewer takeover interface

**Phase 14 Guard Status**:
- 14.2/14.2.1 complete: GuardFailureType taxonomy implemented
- 14.3-14.7 paused: safe language classifier, guard integration, evaluation runner, reviewer console, final validation — all lower priority than chat demo
- Will resume after Phase 15.x chat demo is complete

**Files**: openspec/changes/align-chat-support-product-experience/ (4 files)

**Validation**: OpenSpec strict valid, --all 26/26 passed, ruff clean

---

## 2026-05-07 — Phase 14.2.1: Guard Taxonomy Cleanup

**Problem**: Phase 14.2 enum had a misspelled canonical name (UNCUTED vs UNCITED) and failure_reasons was populated for guard_passed=True safe fallback cases.

**Fixes Applied**:
- Enum canonical name fixed from `UNCUTED_SUBSTANTIVE_CLAIM` to `UNCITED_SUBSTANTIVE_CLAIM` (value unchanged for serialization stability)
- `failure_reasons` changed to failure-only: only populated when guard_passed=False
- Safe fallback signals deferred to future guard_signals/reporting phase
- No guard_passed logic changes, no human review reduction

**Files Modified**: claim_guard.py, test_claim_guard.py, tasks.md

**Quality Gate**: 1087 unit + 146 integration tests (0 skipped), coverage 86.62%, OpenSpec 25/25

---

## 2026-05-07 — Phase 14.2: Guard Taxonomy Data Model

**Implementation Summary**:
- Added `GuardFailureType` str-enum with 8 values to `claim_guard.py`
- Added `failure_reasons: list[GuardFailureType]` field to `GuardResult` with `default_factory=list`
- Updated `check_claim_guard()` to build failure_reasons list from boolean check results

**Taxonomy-to-Boolean Mapping**:
- `citation_coverage < 1.0` → `UNCITED_SUBSTANTIVE_CLAIM` (partial/invalid citations)
- `has_uncited_claims=True` → `UNSUPPORTED_POLICY_CLAIM` (substantive content without citations)
- `has_forbidden_promise=True` → `FORBIDDEN_PROMISE` (forbidden promise patterns)
- `risk_flags_respected=False` → `MISSING_RISK_ESCALATION` (high-risk without acknowledgment)
- `guard_passed=True` + `_is_safe_fallback()` → `EVIDENCE_INSUFFICIENT_FALLBACK`
- No match on guard failure → `AMBIGUOUS_GUARD_CASE`

**Test Coverage**: 9 new tests in TestGuardFailureType + TestFailureReasonsTaxonomy, 58 existing tests pass

**Quality Gate**: 1087 unit + 146 integration tests (0 skipped), coverage 86.65%, OpenSpec 25/25

---

## 2026-05-07 — Phase 14.1: Guard Architecture Improvement Planning

**Root Cause**: Phase 13.10 showed 4 remaining guard failures collapsed to simplified booleans. Current GuardResult has 3 boolean fields (`has_uncited_claims`, `has_forbidden_promise`, `risk_flags_respected`) that cannot distinguish between distinct failure modes.

**Key Discovery — p12_021 Discrepancy**:
- Phase 13.10 report text: "Substantive content without [chunk_id] citation markers" → has_uncited_claims
- Phase 13.10 summary JSON: reason=risk_flags_respected
- Extended eval rows: all fields None (data not captured correctly in Phase 13.10 runner)
- This ambiguity is the primary motivation for granular taxonomy

**Taxonomy Design**: 8 granular types extending GuardResult backward-compatibly:
- UNSUPPORTED_POLICY_CLAIM (from has_uncited_claims)
- FORBIDDEN_PROMISE (from has_forbidden_promise)
- MISSING_RISK_ESCALATION (from risk_flags_respected=False)
- SAFE_ESCALATION_STATEMENT (positive signal)
- MANUAL_REVIEW_ACKNOWLEDGEMENT (positive signal)
- EVIDENCE_INSUFFICIENT_FALLBACK (safe fallback)
- AMBIGUOUS_GUARD_CASE (catch-all for indeterminate)
- UNCited_SUBSTANTIVE_CLAIM (alias for UNSUPPORTED_POLICY_CLAIM)

**Non-Requirements (explicit)**:
- No guard weakening — boolean fields and guard_passed unchanged
- No human review reduction
- No auto-send change
- No real provider calls

**Spec**: openspec/specs/guard-architecture/spec.md — 6 requirements including explicit No Guard Weakening

---

## 2026-05-07 — Phase 13.10: Guard-Aware Provider Prompting Experiment

**Problem**: Phase 13.9 real provider (deepseek-v4-pro) generated free-form Chinese text (80–174 chars) without inline `[chunk_id]` citation markers. Claim guard's `_extract_chunk_ids()` only recognizes `[UUID]` format, not `[N]` numeric citations. Result: citation validation pass 12%, claim guard pass 4%, human review triggers 100%.

**Root Cause**: `OpenAICompatibleProvider.generate_draft()` used hardcoded bare-bones prompt (lines 249–261) that formatted evidence as `[1] Title: content...` and did not instruct the LLM to include `[chunk_id]` markers in generated text.

**Solution**: Replaced hardcoded prompt with guard-aware structured prompt using `format_evidence_block()` (produces `[chunk_id]` format) and explicit safety rules requiring `[{chunk_id}]` inline citations, forbidding numeric `[N]` citations, instructing safe fallback when evidence insufficient.

**Key Engineering Decision D14**: Guard-aware prompt is a prompt contract, not a guard weakening. The prompt instructs the LLM to include citation markers; the guard still validates them. If the LLM ignores the instruction, the guard correctly fails.

**Results** (real provider, 25 synthetic cases):
- Citation validation pass: 12% → 76% (+64 pp)
- Claim guard pass: 4% → 84% (+80 pp)
- Unsupported claim rate: 88% → 24% (-64 pp)
- Human review triggers: 100% → 48% (-52 pp)
- Reviewer-ready rate: 4% → 64% (+60 pp)
- Safe fallback rate: 4% → 84% (+80 pp)

**Remaining 4 failures** (all correct guard behavior):
- p12_011, p12_015: risk escalation not acknowledged (citations present but no escalation language)
- p12_018: 2 unsupported claims + 1 forbidden promise
- p12_021: uncited substantive claim (LLM ignored citation instruction)

**Trade-off discovered**: 84% safe fallback rate — expected consequence of the prompt instructing conservative citing. Acceptable because safe fallback cases correctly trigger human review.

**Spec promoted**: `openspec/specs/guard-aware-prompting/spec.md` — 5 requirements covering Inline Citation Markers, Evidence Sufficiency Fallback, Forbidden Promise Patterns, No-Auto-Send Boundary, Risk Flag Escalation Acknowledgment.

**Boundary**: Offline fixture-based evaluation on 25 synthetic cases with mock evidence — NOT a benchmark. Human review mandatory. No auto-send.

---

## 2026-05-07 — Phase 13: Extended Draft Evaluation Metrics (Planning)

**Problem**: Phase 12 provider comparison established baseline (25 cases, fake+real, 25/25 success, 8 HR triggers each) but left several metrics as "not yet measured": citation precision, evidence coverage, unsupported claim rate, forbidden promise rate, guard pass rate, citation validation pass rate, reviewer-ready rate.

**Key Insight**: DraftGenerationResult already contains all required data:
- `citation_validation` (DraftCitationValidationResult): is_valid, valid/invalid cited IDs, available IDs
- `guard_result` (GuardResult): guard_passed, has_forbidden_promise, has_uncited_claims, citation_coverage
- `draft.unsupported_claims`: list of unsupported claim strings

The Phase 12 runner only extracts `draft_text_length`, `confidence`, `must_human_review`, `has_citations` — it needs to extract the full DraftGenerationResult fields.

**Design Decision D14**: Metric computation goes into a new `draft_comparison_metrics.py` module (pure functions, no network, deterministic). This keeps the evaluation layer separate from the drafting layer.

**OpenSpec Change**: `add-extended-draft-evaluation-metrics` created with 3 specs:
- draft-evaluation-metrics: citation precision, evidence coverage, unsupported claim rate, guard pass rate, citation validation pass rate, None handling
- provider-comparison-metrics: extended row schema, same metrics for both providers, fake-first, real opt-in
- reviewer-ready-metric: definition, does NOT override human review, does NOT mean auto-send, reported per provider

*Tracks implementation decisions, design choices, and engineering trade-offs.*

---

## 2026-05-07 — Phase 12D: Metrics Dashboard and Portfolio Evidence Pack

**Problem**: Phase 12C completed the provider comparison run. Phase 12D needed to create portfolio-facing documentation: metrics dashboard, provider analysis, case studies, error analysis, visual explanations, interview data story, and reviewer-ready metric proposal.

**Approach**: Docs/portfolio-only batch. No runtime code changes, no LLM API calls, no retrieval/embeddings modifications. All metrics traced to existing repo files. Explicit boundary wording on all claims.

**Key Decisions**:
- D11: Phase 12D is the final documentation phase for the Phase 12 demo readiness sprint. No further runtime changes unless explicitly planned in a new OpenSpec change.
- D12: Metrics dashboard is the canonical single-page metrics reference — other portfolio docs link to it rather than duplicating numbers.
- D13: "Reviewer-ready rate" is proposed as a better safety metric than confidence alone.

**Files Created**: 8 new portfolio docs under `docs/portfolio/`.

**Validation**: ruff clean, openspec --all 22/22 passed. Full quality gate skipped (docs-only batch per AGENTS.md).

---

## 2026-05-07 — Phase 12C: Optional Real Provider Run

**Problem**: Phase 12A established OpenAICompatibleProvider for offline comparison. Phase 12C attempts real provider run if env is configured, otherwise validates fake baseline and records pending status.

**Approach**:
- Check TICKETPILOT_LLM_PROVIDER, TICKETPILOT_LLM_BASE_URL, TICKETPILOT_LLM_API_KEY, TICKETPILOT_LLM_MODEL presence (without printing values)
- If configured: run full comparison with sample (--limit 5) then full
- If not configured: run fake baseline, generate canonical reports, record as pending

**Key Decision**: Real provider is opt-in only. No failure if env is missing — this is expected for offline portfolio work.

**Key Findings**:
- Real provider env not configured in current environment
- Fake baseline: 25/25 cases, avg confidence 0.85, 8 human review triggers
- Canonical reports generated: summary JSON, rows JSON, markdown report

**Files Created**:
- `reports/eval/phase12_llm_provider_comparison_summary.json`
- `reports/eval/phase12_llm_provider_comparison_rows.json`
- `reports/eval/phase12_llm_provider_comparison_report.md`

**Validation**: Full quality gate PASSED — 1069 unit + 146 integration, 0 skipped, 86.71% coverage

---

## 2026-05-06 — Phase 11.10: Final Validation and Archive

**Problem**: Phase 11 (Evidence-Grounded LLM Draft Generation) is complete across all 10 sub-phases (11.1-11.9). Needed full quality gate validation, archive OpenSpec change, and update all harness docs.

**Validation Results**:
- Unit tests: 1001 passed
- Integration tests: 140 passed, 0 skipped
- Coverage: ≥70% threshold passed
- Ruff: All checks passed
- OpenSpec --strict: Valid
- OpenSpec --all: 19/19 passed (post-archive, specs promoted)
- Secret scan: Clean
- Overclaim scan: Clean

**Archive Results**:
- OpenSpec change `add-evidence-grounded-llm-draft` archived to `openspec/changes/archive/2026-05-06-add-evidence-grounded-llm-draft/`
- Specs updated: claim-guard (+9 lines), draft-generation (+10 lines), draft-evaluation (+13 lines), human-review (+8 lines)
- Post-archive OpenSpec --all: 19/19 passed

**Phase 11 Complete Summary**:
- 8-layer safety architecture: prompt constraint → citation validation → ClaimGuard → risk-aware → human review propagation → no-auto-send → fake default → provider identity
- LLMProvider ABC + FakeLLMProvider (deterministic, no API dependency)
- Evidence-grounded prompt builder with evidence constraints + safety rules
- DraftCitationValidationResult for structural evidence ID validation
- ClaimGuard with 5 checks: citation coverage, uncited claims, forbidden promises, evidence sufficiency, risk-aware
- DraftGenerationResult wrapper + generate_draft() pipeline
- Human review console update with 15 audit fields + guard display
- Offline draft evaluation metrics (8 deterministic metrics, citation precision=100%)
- Portfolio snapshot with 10-section comprehensive documentation

---

## 2026-05-06 — Phase 11.9: Portfolio Snapshot

**Problem**: Phase 11 code complete, needed portable documentation for portfolio/snapshot use, separate from raw reports. Phase 11 changed from "进行中/in progress" to "已完成/complete" across all portfolio docs.

**Approach**: Created comprehensive Phase 11 portfolio snapshot with 10 sections: one-sentence summary, diagnosis chain, key architecture decisions, key metrics, component map, product interpretation, engineering interpretation, boundaries, resume bullets, interview versions.

**Key Deliverables**:
- `docs/portfolio/phase11_evidence_draft_snapshot.md` — complete Phase 11 snapshot
- Updated README.md + README.en.md: Phase 11 status + 8-layer safety architecture
- Updated product_portfolio_material_pack.md: iteration history table with Phase 11 column
- Updated project_case_study_cn/en.md: Phase 11 complete status + detailed description
- Updated interview_talking_points.md: 1-minute pitch reflects completion

**Key Updates Across Portfolio Docs**:
- Phase 11 status: "进行中/in progress" → "已完成/complete"
- Added Phase 11 column to iteration history table
- 8-layer safety architecture: prompt constraint → citation validation → ClaimGuard → risk-aware → human review propagation → no-auto-send → fake default → provider identity

**Validation**: ruff clean, OpenSpec --strict valid, OpenSpec --all 17/17

---

## 2026-05-06 — Phase 11.8: Offline Draft Evaluation

**Problem**: Need to quantify draft generation quality using deterministic local metrics — no real LLM API calls, no network access, no real customer data. The evaluation should measure citation quality, evidence coverage, guard effectiveness, and human review trigger correctness.

**Approach**:
- draft_metrics.py with 4 pure metric functions: compute_citation_precision (None if no citations), compute_evidence_coverage (None if no evidence), compute_human_review_trigger_correct (bool), compute_draft_evaluation_summary (aggregates all rows)
- DraftEvaluationRow and DraftEvaluationSummary schemas in evaluation/schemas.py (+41 lines)
- run_draft_evaluation.py CLI runner: load tickets → run_pipeline → build rows → compute summary → write JSON + Markdown
- FakeLLMProvider only — deterministic, no API keys, no network calls

**Key Engineering Decisions**:
- Citation precision and evidence coverage return None when no citations/evidence (excluded from average to avoid misleading low values)
- Human review trigger correctness: expected (pre-draft risk state) vs actual (final must_human_review), denominator = cases with trigger conditions
- DraftGenerationResult got optional ticket_output field to support evaluation access without modifying pipeline behavior
- Markdown report explicitly disclaims: local demo, synthetic data, offline evaluation only, no auto-send, FakeLLMProvider tests mechanics not quality
- Safe fallback rate denominator = total cases (not just no-evidence cases), reflecting proportion of the full eval set

**Files**:
- `src/ticketpilot/evaluation/draft_metrics.py` (new, 150 lines)
- `src/ticketpilot/evaluation/schemas.py` (+41 lines: DraftEvaluationRow + DraftEvaluationSummary)
- `src/ticketpilot/drafting/generator.py` (+2 lines: ticket_output field)
- `scripts/run_draft_evaluation.py` (new, 310 lines)
- `tests/unit/test_draft_metrics.py` (new, 267 lines, 32 tests)
- `tests/integration/test_draft_evaluation_runner.py` (new, 190 lines, 7 tests)

**Validation**: 32 unit + 7 integration tests passed, ruff clean, quality gate pending.

---

## 2026-05-06 — Phase 11.3: Evidence-Grounded Prompt Builder

**Problem**: LLM provider interface (Phase 11.2) defines generate_draft() which takes ticket context + evidence, but doesn't specify how to structure the input prompt. Need a deterministic prompt builder that converts evidence candidates and ticket context into a structured prompt that constrains the LLM to evidence-grounded drafting.

**Approach**:
- DraftPromptInput schema: Pydantic model with ticket_text, issue_type, risk_flags, severity, must_human_review, evidence_candidates
- format_evidence_block(): Sorts evidence by rank ascending, formats each with stable metadata (chunk_id, doc_id, doc_type, title, score/rank), truncates content at 200 chars, skips empty content, configurable max count
- build_safety_instructions(): 8 rules covering draft-only language, citation requirement, forbidden promises, risk-flag-aware review escalation, severity awareness
- build_output_format_instructions(): Structured output spec aligning with DraftReply fields
- build_prompt(): Assembles 4 sections (system role, ticket context, evidence, safety + output format)

**Key Engineering Decisions**:
- Used Pydantic BaseModel for DraftPromptInput to maintain project consistency and get free validation
- Evidence truncation at 200 chars matches Citation.evidence_excerpt max_length from existing schema
- Evidence ID references use [证据 ID] notation consistent with Chinese-language prompt design
- Empty content is silently skipped rather than raising — the LLM sees fewer evidence items but still gets a valid prompt
- Fail-fast on empty ticket_text: raises ValueError rather than generating a meaningless prompt
- Output format instructions use field names matching DraftReply (answer_text, cited_evidence_ids, etc.) for future structured parsing

**Files**:
- `src/ticketpilot/drafting/prompt_builder.py` (new, 157 lines)
- `tests/unit/test_prompt_builder.py` (new, 338 lines, 50 tests)

**Validation**: Quality gate PASSED — 857 unit, 119 integration (0 skip), 86.04% coverage, ruff clean, OpenSpec 17/17, secret scan clean, overclaim scan clean.

---

## 2026-05-06 — Phase 11.4: Draft Citation Validation

**Problem**: DraftReply objects carry cited_evidence_ids but no validator existed to check whether these IDs are structurally valid — do they exist in the provided evidence candidates? Are there duplicates? Is the draft making substantive claims without citations? Need a deterministic, local-only validator.

**Approach**:
- DraftCitationValidationResult schema: is_valid, valid_cited_evidence_ids, invalid_cited_evidence_ids, duplicate_cited_evidence_ids, missing_citation_required, available_evidence_ids, errors, warnings, must_human_review
- validate_draft_citations(): 5 sequential checks — evidence ID existence, duplicate detection, empty-evidence handling, missing citation heuristic, unsupported claims propagation
- Evidence ID matching: converts EvidenceCandidate.chunk_id (UUID) to string and matches against DraftReply.cited_evidence_ids (list[str])
- Missing citation heuristic: checks if draft_text contains safe-fallback patterns; only flags substantive text without citations. Safe fallback patterns: "无法确认具体政策条款", "建议转人工处理", "转人工", "证据不足"
- Human review propagation: must_human_review cascades from DraftReply → validation result; validation failure and unsupported_claims both force must_human_review; never downgrades

**Key Engineering Decisions**:
- Used SAFE_FALLBACK_TEXT from llm_provider.py for exact-match fallback detection, plus heuristic pattern matching for similar fallback messages
- Duplicates are warnings not errors — the draft can still be valid even if IDs are repeated, but the reviewer should know
- Output lists are sorted for deterministic results — same input always produces same output
- Validator is purely structural (ID existence, format checks) — semantic claim detection is deferred to Phase 11.5 ClaimGuard

**Files**:
- `src/ticketpilot/drafting/draft_citation_validator.py` (new, 75 lines)
- `tests/unit/test_draft_citation_validator.py` (new, 215 lines, 21 tests)
- `src/ticketpilot/drafting/__init__.py` (modified, updated exports)

**Validation**: Quality gate PASSED — 878 unit, 119 integration (0 skip), 86.35% coverage, ruff clean, OpenSpec 17/17, secret scan clean, overclaim scan clean.

---

## 2026-05-06 — Phase 11.5: Unsupported-Claim Guard

**Problem**: DraftReply objects carry draft_text with potential uncited claims, forbidden promises, and unacknowledged risk flags. Need a deterministic claim guard that runs post-generation to catch these issues before human review. Existing draft_citation_validator validates cited_evidence_ids structurally but doesn't inspect draft content.

**Approach**:
- GuardResult schema: 7 fields — citation_coverage, has_uncited_claims, has_forbidden_promise, forbidden_promise_details, evidence_sufficiency, risk_flags_respected, guard_passed
- check_claim_guard(): 5 deterministic checks — citation coverage (parse [chunk_id] from text), uncited claim detection (substantive text without citations), forbidden promise detection (9 regex patterns), evidence sufficiency (available evidence), risk-aware check (high-risk flag acknowledgment)
- Guard is purely local: no network calls, no LLM API, no semantic analysis — same pattern as draft_citation_validator

**Key Engineering Decisions**:
- GuardResult is defined in claim_guard.py (not schemas.py) to keep the module self-contained; pipeline integration (Phase 11.6) will add GuardResult to DraftReply
- Citation coverage extracts [UUID] references from raw draft_text rather than using the cited_evidence_ids field — this is a content-level check vs the structural check in draft_citation_validator
- Forbidden promise patterns use regex for amounts (退款\d+元) and literal matching for legal/account/liability phrases — deterministic and testable
- Safe-fallback text ("建议转人工处理") and greeting-only messages are exempt from uncited-claim detection to avoid false positives on legitimate no-evidence responses
- Risk-aware check uses 5 escalation patterns (转人工, 人工处理, 升级处理, human review, escalated) — matching any is sufficient to pass
- Evidence sufficiency is deliberately simple (evidence exists → "sufficient") — a more nuanced assessment would require semantic analysis outside Phase 11.5 scope

**Files**:
- `src/ticketpilot/drafting/claim_guard.py` (new, ~195 lines)
- `tests/unit/test_claim_guard.py` (new, 58 tests)

**Validation**: Unit tests 58/58 passed, ruff clean, OpenSpec 17/17 —all, --strict.

---

## 2026-05-06 — Phase 11.6: Pipeline Integration

**Problem**: Phase 11.2–11.5 produced isolated components (LLM provider, prompt builder, citation validator, claim guard) but no single entrypoint that wires them together into a deterministic generation workflow. Need a compose function that runs all components in sequence and exposes trace metadata.

**Approach**:
- DraftGenerationResult wrapper: holds draft + provider_name + model_name + citation_validation + guard_result + to_trace_dict()
- generate_draft() pipeline: (1) build prompt input from TicketOutput, (2) call LLM provider (default: FakeLLMProvider via provider_config), (3) CitationValidator (content-level [N] checks), (4) draft_citation_validator (structural ID checks), (5) claim_guard (content-level checks), (6) human review propagation — never downgrades, (7) escalation_reason on guard failure
- Optional `provider` argument enables test injection of mock providers
- Optional `inject_prompt` argument for deterministic prompt testing scenarios

**Key Engineering Decisions**:
- Used Option B wrapper (DraftGenerationResult) rather than extending DraftReply — preserves backward compatibility with all 194 existing DraftReply tests
- Provider injection via constructor argument rather than global state — enables clean testing without monkeypatching
- CitationValidator and draft_citation_validator both run in sequence: the former checks content-level [N] markers, the latter checks structural cited_evidence_ids — these are complementary checks from different layers
- Human review propagation: first respects DraftReply.must_human_review (already set by LLM provider), then upgrades if structural validation or guard fails — never downgrades
- to_trace_dict() excludes draft text and prompts — compact for audit, no sensitive data leakage
- guard_result attached to DraftGenerationResult (not DraftReply) — keeps DraftReply schema stable; Phase 11.7 (Human Review Console) will integrate guard results into the display layer

**Files**:
- `src/ticketpilot/drafting/generator.py` (new, ~245 lines)
- `tests/unit/test_draft_generator.py` (new, 33 tests)
- `tests/integration/test_draft_generation_integration.py` (new, 14 tests)
- `src/ticketpilot/drafting/__init__.py` (modified, +5 exports)

**Validation**: Unit tests 33/33 passed, integration 14/14 passed, ruff clean, OpenSpec 17/17.

---
## 2026-05-06 — Phase 11.1: Evidence-Grounded LLM Draft Generation Planning

**Problem**: Template-based drafts (FakeDraftProvider) demonstrate pipeline connectivity but not portfolio-grade draft quality. The product needs evidence-grounded generation with safety guardrails.

**Approach**: Designed a multi-layer architecture with 8 safety layers:
1. Prompt constraint (LLM instructed to use evidence only)
2. Citation validation (existing, extended)
3. Claim guard (new: forbidden promise detection, evidence coverage)
4. Risk-aware check (high-risk flags force escalation acknowledgment)
5. Human review handoff (must_human_review architectural gate)
6. No auto-send (architectural invariant)
7. Fake provider default (no API key needed for CI)
8. Provider identity in trace

**Key Architectural Decision**: The LLM provider abstraction follows the exact pattern of the embedding provider — FakeLLMProvider for CI/development, real provider opt-in via environment variables. This ensures the pipeline runs without external dependencies by default.

**Files**: `openspec/changes/add-evidence-grounded-llm-draft/` (7 files)

---

## 2026-05-06 — Phase 11.2: Draft Schema and Deterministic Provider

**Problem**: Need LLM provider abstraction layer, deterministic fake provider for development/CI, and extended DraftReply schema to support evidence-grounded draft generation. Existing FakeDraftProvider is template-based with no evidence integration.

**Approach**:
- LLMProvider ABC with `provider_name`, `model_name`, `generate_draft()` — same pattern as embedding provider
- FakeLLMProvider: deterministic, network-free, no API keys. Produces template-based output from evidence candidates. 4 safety mechanisms: no-evidence fallback, risk-flag escalation, evidence ID tracking, confidence scoring
- Provider config module: `TICKETPILOT_LLM_PROVIDER` env var, default "fake", raises ValueError for unknown types
- DraftReply schema extended with 4 new fields (`provider_id`, `escalation_reason`, `safety_notes`, `cited_evidence_ids`) and 2 model validators

**Key Engineering Decisions**:
- Used `from __future__ import annotations` + TYPE_CHECKING in provider_config.py to avoid circular imports with llm_provider.py
- FakeLLMProvider sorts evidence by rank and takes top-3, matching the pattern used by the evaluation pipeline
- Schema validation uses Pydantic `model_validator(mode="after")` for cross-field rules
- empty-string rejection in cited_evidence_ids is strict — empty strings are silently excluded rather than raising a warning
- Risk flags and must_human_review are independent dimensions that both feed into the final review decision

**Files**:
- `src/ticketpilot/drafting/llm_provider.py` (new, 171 lines)
- `src/ticketpilot/drafting/provider_config.py` (new, 83 lines)
- `src/ticketpilot/drafting/schemas.py` (extended, +45 lines)
- `tests/unit/test_llm_provider.py` (new, 215 lines, 17 tests)
- `tests/unit/test_llm_config.py` (new, 115 lines, 10 tests)

**Validation**: Quality gate PASSED — 807 unit, 119 integration (0 skip), 85.74% coverage, ruff clean, OpenSpec 17/17, secret scan clean.

**Problem**: Template-based drafts (FakeDraftProvider) demonstrate pipeline connectivity but not portfolio-grade draft quality. The product needs evidence-grounded generation with safety guardrails.

**Approach**: Designed a multi-layer architecture with 8 safety layers:
1. Prompt constraint (LLM instructed to use evidence only)
2. Citation validation (existing, extended)
3. Claim guard (new: forbidden promise detection, evidence coverage)
4. Risk-aware check (high-risk flags force escalation acknowledgment)
5. Human review handoff (must_human_review architectural gate)
6. No auto-send (architectural invariant)
7. Fake provider default (no API key needed for CI)
8. Provider identity in trace

**Key Architectural Decision**: The LLM provider abstraction follows the exact pattern of the embedding provider — FakeLLMProvider for CI/development, real provider opt-in via environment variables. This ensures the pipeline runs without external dependencies by default.

**Files**: `openspec/changes/add-evidence-grounded-llm-draft/` (7 files)

---

## 2026-05-06 — Phase 10.7.5: Full-Dataset Real Pipeline Doc-Level Evaluation

**Problem**: Doc-type metrics showed 59.4% Recall@10, but Phase 10.5.1 P0 analysis suggested most "wrong" cases were metric granularity, not retrieval failures. Needed full-dataset confirmation.

**Approach**: Exported real provider pipeline (openai_compatible / text-embedding-v4 / 1024-d) for all 101 cases, computed doc-ID level metrics against 86 labeled cases.

**Key Engineering Decision**: Used existing `scripts/run_retrieval_comparison.py export` mode rather than building a new export pipeline. The export already serialized full RetrievalTrace including per-case keyword/vector/fused results at the doc-ID level.

**Result**: Doc-ID Recall@10 = 91.9%. Thesis confirmed: 32/41 (78%) wrong cases reclassified.

**Files**: `reports/retrieval/phase10_full_real_doc_level_*.md`

---

## 2026-05-06 — Phase 10.8: Portfolio Snapshot

**Problem**: Phase 10 findings needed portable documentation for portfolio/snapshot use, separate from raw reports.

**Approach**: Created `docs/portfolio/phase10_hybrid_ranking_diagnosis_snapshot.md` with structured sections: diagnosis chain, key metrics, product interpretation, engineering interpretation, boundaries, resume bullets, interview scripts.

**Key Engineering Decision**: Wrote as standalone document with frozen metrics — no dynamic references to reports that could change. Snapshot is immutable once committed.

---

## 2026-05-06 — Phase 10.9: Final Validation and Archive

**Validation**: Full quality gate — 778 unit, 119 integration (0 skip), 85.27% coverage, ruff clean, OpenSpec 16/16, secret scan clean, overclaim scan clean.

**Archive**: OpenSpec change `add-hybrid-retrieval-ranking-diagnosis` archived to `openspec/changes/archive/2026-05-06-add-hybrid-retrieval-ranking-diagnosis/`. Spec delta applied to `retrieval-evaluation`; new `retrieval-trace` spec created.
