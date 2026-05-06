# Engineering Log — TicketPilot

*Tracks implementation decisions, design choices, and engineering trade-offs.*

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
