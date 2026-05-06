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

## D9 — 2026-05-06: LLM Provider Abstraction Follows Embedding Provider Pattern

- **Decision**: LLM provider uses the same abstraction pattern as the embedding provider: abstract interface + FakeLLMProvider (default, deterministic, CI-safe) + optional real provider via .env.local
- **Context**: Phase 9 established the pattern of fake-as-default, real-via-env for embeddings. Phase 11 brings LLM generation in with the same pattern: no API key required for development/CI, real provider opt-in for evaluation.
- **Alternatives**: Always require a real LLM (blocks CI), use a mock library (coupling), no abstraction at all (untestable)
- **Why this won**: Consistency with existing provider pattern; CI runs without API keys; evaluation can opt into real provider for draft quality assessment

## D8 — 2026-05-06: Default Next Phase Is Evidence-Grounded LLM Draft Generation

- **Decision**: The default next phase (Phase 11) is evidence-grounded LLM draft generation, not continued retrieval tuning
- **Context**: Phase 10 confirmed 91.9% Doc-ID Recall@10 with 78% of wrong cases reclassified as metric granularity. The retrieval evidence chain is complete; the product frontier moves from evidence retrieval to evidence-grounded generation. Continued retrieval optimization (query expansion, fusion ranking, reranker) has diminishing portfolio value.
- **Alternatives**: Phase 11 Query Expansion Audit (documentation-only, addresses 7 zero-hit cases), Phase 11 Fusion Ranking Experiment (code change for 32 partial-hit cases), Phase 11 Reranker Proposal (future work)
- **Why this won**: Product portfolio value of LLM draft generation exceeds marginal retrieval gains. If retrieval is prioritized later, the alternative Phase 11 path can be chosen.

## D7 — 2026-05-06: Phase 10 Is Closed; Do Not Continue Retrieval Tuning Inside Phase 10

- **Decision**: Phase 10 evidence chain is complete and archived. All future retrieval work creates a new Phase (e.g., query expansion, fusion ranking, reranker) with a new OpenSpec change.
- **Context**: Phase 10 delivered: trace audit → P0 export → bottleneck classification → doc-level labels → real pipeline eval → metric granularity thesis confirmed → portfolio snapshot. Archive is complete.
- **Alternatives**: Keep Phase 10 open for follow-up experiments (scope creep), start Phase 11 as continued retrieval work (contradicts thesis findings)
- **Why this won**: Phase 10 achieved its goal; continuing would blur scope. Clean archive enables clear phase boundaries for future work.

## D1 — 2026-05-06: Phase 10 Is Trace-First Diagnosis, Not Tuning

- **Decision**: No retrieval algorithm parameters (RRF k, keyword weight, vector weight, HNSW ef_search) may be changed in Phase 10
- **Context**: Wrong cases remained at 41 after Phase 9 knowledge expansion. Before tuning parameters blindly, Phase 10 diagnoses each case's failure layer using RetrievalTrace.
- **Alternatives**: Directly tune RRF k or embedding parameters (might fix some cases but without understanding root cause), add more knowledge records (already done in Phase 9)
- **Why this won**: Data-informed decisions beat blind optimization. Once bottleneck taxonomy reveals dominant failure modes, targeted changes have higher success probability.
