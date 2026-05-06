# Engineering Log — TicketPilot

*Tracks implementation decisions, design choices, and engineering trade-offs.*

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
