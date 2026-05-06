# Controller Decision Log — TicketPilot

*Source of truth: GitHub docs/harness/*  
*Notion is a human-facing dashboard only.*

Each decision entry records: date, decision, context, alternatives considered, and rationale.

---

## D6 — 2026-05-06: Add Doc-Level Golden Labels Is Next Priority

- **Decision**: Next concrete action is adding `expected_relevant_doc_ids` to `golden_expectations.csv`
- **Context**: Phase 10.4 bottleneck classification revealed 75% of "wrong" cases are actually a metric granularity problem — P0 records reach final evidence but the doc_type-level metric cannot distinguish "right doc retrieved" from "right doc_type, wrong doc retrieved"
- **Alternatives**: Fusion experiment (requires code change), query expansion audit (affects only 1 record), leave as limitation (loses diagnostic value)
- **Why this won**: Data-only change, highest potential impact, unblocks doc-level MRR/Recall@K metrics

## D5 — 2026-05-06: Internal Harness Iteration Without Micro-Confirmations

- **Decision**: AI agent should complete coherent functional batches without stopping for confirmation on every sub-step
- **Context**: User explicitly requested harness-mode iteration — only stop on explicit Stop Conditions
- **Alternatives**: Confirm after every sub-task (too slow), full autonomy (too risky)
- **Why this won**: Balances speed with safety; harness templates already define clear scope boundaries

## D4 — 2026-05-06: GitHub docs/harness Is ChatGPT Controller Source of Truth

- **Decision**: `docs/harness/chatgpt_controller_context.md` and siblings are the canonical handoff files for ChatGPT sessions
- **Context**: Opening a new ChatGPT window lost all project state from prior sessions. Prior context lived in Claude Code memory (.claude/memory/), not in GitHub.
- **Alternatives**: Notion (human-facing, not machine-readable), .claude/memory/ (Claude-specific, not portable), README (too high-level)
- **Why this won**: GitHub files are version-controlled, portable across AI tools (Claude Code, ChatGPT, Codex CLI), and survive window resets

## D3 — 2026-05-06: Real Provider Required for Semantic Retrieval Conclusions

- **Decision**: Every trace report must declare embedding provider. Only real provider (OpenAICompatible, 1024-d) traces may inform semantic ranking decisions. Fake provider traces carry a disclaimer.
- **Context**: Phase 9.5 added real embedding provider support. Fake embeddings are deterministic per text but carry no semantic meaning.
- **Alternatives**: Allow fake provider conclusions with caveats (misleading), require real provider always (not always available)
- **Why this won**: Provider identity gate preserves scientific honesty; fake provider useful for pipeline mechanics testing only

## D2 — 2026-05-06: Fake Provider for Pipeline Mechanics Only

- **Decision**: FakeEmbeddingProvider (384-d) is the default for development and CI. It verifies pipeline correctness but cannot measure retrieval quality.
- **Context**: Fake embeddings are deterministic — same text always produces same vector, but vectors have no semantic relationship to text content.
- **Alternatives**: Remove fake provider entirely (breaks CI without real API key), upgrade fake to have limited semantics (scope creep)
- **Why this won**: Keeps CI dependency-free; explicit separation of concerns between mechanics and quality

## D1 — 2026-05-06: Phase 10 Is Trace-First Diagnosis, Not Tuning

- **Decision**: No retrieval algorithm parameters (RRF k, keyword weight, vector weight, HNSW ef_search) may be changed in Phase 10
- **Context**: Wrong cases remained at 41 after Phase 9 knowledge expansion. Before tuning parameters blindly, Phase 10 diagnoses each case's failure layer using RetrievalTrace.
- **Alternatives**: Directly tune RRF k or embedding parameters (might fix some cases but without understanding root cause), add more knowledge records (already done in Phase 9)
- **Why this won**: Data-informed decisions beat blind optimization. Once bottleneck taxonomy reveals dominant failure modes, targeted changes have higher success probability.
