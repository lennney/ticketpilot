# Proposal: Real Retrieval Upgrade (Phase 8)

## Executive Summary

Phase 7 established TicketPilot's evaluation infrastructure: 101 eval tickets, 95 knowledge records, and a deterministic offline evaluation pipeline. However, the default FakeEmbeddingProvider (384-dim deterministic SHA-256 hash) only validates pipeline mechanics — it cannot prove real Chinese semantic retrieval quality.

Phase 8 adds a real Chinese embedding provider as an opt-in component, retains FakeEmbeddingProvider as the default test provider, and builds a fake-vs-real retrieval comparison evaluation on the identical Phase 7 dataset. The output is a structured retrieval quality report with Top-K hit rates, MRR, doc type recall, and wrong-case analysis.

No changes to Phase 7 eval data, knowledge base, or evaluation reports. No real LLM, no auto-send, no production deployment, no API keys committed.

## Baseline (Current State)

### Embedding
- **Default provider**: FakeEmbeddingProvider
- **Dimension**: 384 (deterministic SHA-256 hash)
- **Semantic meaning**: None — cosine similarity verifies pipeline connectivity only
- **Provider interface**: Single implementation, no abstraction layer for switching

### Retrieval
- **Strategy**: Hybrid keyword FTS + pgvector HNSW + RRF fusion
- **Knowledge base**: 95 records (FAQ=40, Policy=30, Case=25)
- **Index**: All chunks embedded with 384-dim fake vectors
- **Current metrics (pipeline mode)**:
  - Evidence doc type recall: 43.2%
  - Intent accuracy: 53.5%
  - Severity accuracy: 54.5%
  - Risk flag F1: 29.8%
  - Fallback correctness: 90.1%
  - No-auto-send compliance: 100.0% (architecture constraint)

### Retrieval Trace
- Not systematically preserved for per-query analysis

## Problem

1. **Pipeline mechanics ≠ retrieval quality**. Fake embeddings prove the pipeline runs, not that it retrieves relevant evidence.
2. **No semantic understanding**. Keyword FTS is effective for exact-match terms but misses semantic variants like "退款" ↔ "退钱" ↔ "返还费用".
3. **No retrieval quality baseline**. Without a real provider comparison, it is impossible to quantify how much semantic retrieval would improve the current pipeline metrics.
4. **No wrong-case analysis**. Current evaluation reports aggregate metrics but do not classify retrieval failures by root cause (keyword mismatch, semantic drift, missing knowledge, etc.).

## Goal

1. Add a real Chinese embedding provider (e.g., text2vec / BGE / OpenAI-compatible) as an opt-in component.
2. Define an EmbeddingProvider abstraction with config, metadata, and dimension contract.
3. Keep FakeEmbeddingProvider as the default — all existing tests and CI must continue passing without network.
4. Build an index rebuild workflow that enforces provider metadata and dimension consistency.
5. Run fake-vs-real retrieval comparison on the identical Phase 7 dataset: same 101 tickets, same 95 knowledge records.
6. Output a structured retrieval comparison report with Top-K hit rates, MRR, doc type recall, and wrong-case analysis.
7. Document all findings honestly — no production claims, no real enterprise validation.

## Non-goals

- ❌ No real LLM integration
- ❌ No auto-send — all output remains draft-only
- ❌ No production deployment
- ❌ No multi-provider benchmark race (compare exactly 1 real provider against fake)
- ❌ No embedding fine-tuning
- ❌ No reranker integration
- ❌ No LangGraph or workflow refactoring
- ❌ No API keys committed to repository
- ❌ No real enterprise data validation
- ❌ No Phase 7 eval data or knowledge base modifications
- ❌ No production-readiness claims

## Key Design Decisions

### A. Provider Abstraction

| Decision | Choice |
|----------|--------|
| Default provider | FakeEmbeddingProvider (unchanged behavior) |
| Real provider | Opt-in via config/environment |
| Provider selection | `EMBEDDING_PROVIDER` env var (values: "fake", "openai", etc.) |
| Test dependency | All tests default to fake; network tests require explicit opt-in marker |
| Registry | Simple factory dict or provider registry — no DI framework |

Rationale: FakeEmbeddingProvider must remain the default so that all existing tests, CI, and local development continue to work without network. Real provider is a conscious opt-in for retrieval evaluation.

### B. Dimension Handling

| Decision | Choice |
|----------|--------|
| Fake dimension | 384 (unchanged) — existing index unaffected |
| Real dimension | Configurable via `EMBEDDING_DIM` (e.g., 768 for text2vec, 1024 for BGE, 1536 for OpenAI) |
| pgvector column | Must support dynamic dimension or use separate index per provider |
| Migration strategy | Index rebuild required on dimension change — fail loudly on mismatch |
| Metadata | Store `provider_name`, `model_name`, `dimension`, `built_at` per index |

Current pgvector schema may bind `vector(384)`. If the real provider uses a different dimension, a safe strategy is required:
- Option A: `vector(384)` with `ALTER TABLE ... ALTER COLUMN` — risky with existing data
- Option B: Add a separate vector column per dimension — clutters schema
- Option C: Truncate + reindex — viable for dev/portfolio with 95 records
- Option D: Use a separate `vector()` column with max dimension and pad shorter vectors — wasteful

Phase 8 should prefer a clean reindex approach: drop existing index, recreate with correct dimension, re-embed all 95 records. With 95 records this is fast and safe for a portfolio project.

### C. Index Rebuild

| Decision | Choice |
|----------|--------|
| Trigger | Explicit CLI command or script |
| Metadata recording | Store provider_name, model_name, dimension, built_at (in DB or JSON) |
| Safety check | Fail if dimension mismatch detected between config and existing index |
| Scope | Re-embed all 95 knowledge records |
| Idempotency | Multiple rebuilds produce consistent output for same provider+model |

The rebuild command must:
1. Read current knowledge records from DB
2. Re-embed each record using the configured provider
3. Verify dimension matches config
4. Update pgvector index
5. Record provider metadata
6. Fail loudly on any mismatch or network error

### D. API Key Security

| Decision | Choice |
|----------|--------|
| Source | Shell environment or `.env.local` (not `.env`) |
| `.env.example` | May list variable names only — no real keys |
| `.env.local` | Must be in `.gitignore` (verify existing) |
| Secret scan | Must remain clean after all changes |
| CI | No real API keys in CI — tests use mocked provider |

### E. Evaluation

| Decision | Choice |
|----------|--------|
| Dataset | Identical Phase 7: 101 tickets, 95 knowledge records |
| Comparison | FakeEmbeddingProvider vs RealEmbeddingProvider on same queries |
| Scope | Retrieval quality, not reply quality or end-to-end metrics |
| Baseline | Current pipeline metrics (doc type recall = 43.2%) |
| Trace | Preserve retrieval trace per query for wrong-case analysis |

The comparison evaluates retrieval only, not end-to-end pipeline metrics. Changes in intent classification, risk flagging, or draft generation caused by improved retrieval are secondary observations, not primary metrics.

## Proposed Metrics

| Metric | Definition |
|--------|------------|
| Top-1 evidence hit rate | Proportion of queries where the top-1 retrieved doc matches an expected doc |
| Top-3 evidence hit rate | Proportion where at least one expected doc appears in top 3 |
| Top-5 evidence hit rate | Proportion where at least one expected doc appears in top 5 |
| MRR (Mean Reciprocal Rank) | Mean of 1/rank of first relevant document |
| Evidence doc type recall | Proportion of expected doc types (FAQ/Policy/Case) that appear in retrieved set |
| Expected doc ID hit rate | Proportion of golden-expected doc IDs found in retrieved set (if golden supports it) |
| No-evidence fallback correctness | Whether fallback_required decision matches golden expectation |
| Retrieval trace completeness | Whether each query's retrieval steps (keyword query, vector query, fusion) are logged |
| Wrong-case count | Number of queries where retrieval fails to surface expected evidence |
| Wrong-case categories | Classification of failures by root cause |

### Wrong-case Categories

| Category | Description |
|----------|-------------|
| Keyword mismatch | Query terms don't match knowledge record terms; FTS fails |
| Semantic drift | Embedding captures wrong semantics; top vectors irrelevant |
| Missing knowledge | Expected evidence not in knowledge base |
| Wrong issue type | Query classified to wrong issue type → wrong retrieval query |
| Risk signal not reflected | Query contains risk signal but retrieval query doesn't encode it |
| Doc type mismatch | Retrieved docs exist but wrong type (e.g., FAQ instead of Policy) |
| Insufficient golden expectation | Golden expectation lacks specific doc ID targets — cannot measure hit rate precisely |
| Fake embedding limitation | Fake vector similarity is random; relevant docs drown in noise |
| Real embedding over-generalization | Real embedding retrieves broadly but misses precise Policy match |

## Expected Output

Phase 8 final deliverables (across all batches):

| Artifact | Path | Description |
|----------|------|-------------|
| Provider config docs | `docs/technical/embedding_provider.md` | Provider configuration guide |
| Real provider implementation | `src/ticketpilot/retrieval/providers/real_embedding.py` | Real embedding client |
| Fake provider (unchanged) | `src/ticketpilot/retrieval/providers/fake_embedding.py` | Default test provider |
| Provider registry | `src/ticketpilot/retrieval/providers/__init__.py` (updated) | Provider factory |
| Index rebuild command | `scripts/rebuild_embeddings.py` | Explicit rebuild CLI |
| Comparison CLI/script | `scripts/compare_retrieval.py` | Run both providers and compare |
| Comparison report (JSON) | `reports/retrieval/fake_vs_real_comparison.json` | Structured metrics |
| Comparison report (MD) | `reports/retrieval/fake_vs_real_comparison.md` | Human-readable report |
| Wrong-case analysis | `reports/retrieval/wrong_cases.md` | Categorised failure analysis |
| Limitations update | `docs/limitations.md` (updated) | Add real embedding limitation notes |
| README update | `README.md` / `README.en.md` (updated) | Document provider config |
| Portfolio update | `docs/portfolio/` (updated) | Phase 8 portfolio snapshot |

## Constraints

- FakeEmbeddingProvider must remain the default — no existing test may break
- No API key may be committed to the repository
- Dimension mismatch between config and existing index must fail with a clear error
- Index rebuild must be explicit (not automatic on pipeline run)
- Network tests must not run in default CI
- Real provider must not be used in CI (mock or fake only)
- No Phase 7 eval data or knowledge base may be modified
- No changes to evaluation reports from Phase 7
- All retrieval comparison reports must honestly state the synthetic data limitation
