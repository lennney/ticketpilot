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
