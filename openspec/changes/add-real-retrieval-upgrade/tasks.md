# Tasks: Real Retrieval Upgrade (Phase 8)

## Batch 1: OpenSpec Planning Only

- [x] 1.1 Create `.openspec.yaml` — change metadata, constraints, affected modules and specs
- [x] 1.2 Create `proposal.md` — problem, goal, non-goals, key design decisions, metrics, expected output
- [x] 1.3 Create `specs/embedding/spec.md` — provider abstraction, Fake remains default, Real as opt-in, dimension contract, metadata, network tests not in CI, no API key committed
- [x] 1.4 Create `specs/config/spec.md` — environment variables (EMBEDDING_PROVIDER, MODEL, DIM, BASE_URL, API_KEY, BATCH_SIZE), safe defaults, .env.example listing
- [x] 1.5 Create `specs/retrieval-evaluation/spec.md` — fake-vs-real comparison, Top-K hit rate, MRR, doc type recall, wrong-case analysis categories, report paths
- [x] 1.6 Create `tasks.md` — batch breakdown (this file)
- [x] 1.7 Update `docs/changelog.md` with Phase 8A planning entry
- [x] 1.8 Run OpenSpec validate add-real-retrieval-upgrade --strict
- [x] 1.9 Run OpenSpec validate --all

## Batch 2: Provider Config and Interface Design

- [x] 2.1 Inspect existing `FakeEmbeddingProvider` — found at `src/ticketpilot/retrieval/providers/fake_embedding.py`, class with `embed()`/`embed_batch()` and `DIM=384`
- [x] 2.2 Define or confirm `EmbeddingProvider` interface — Protocol already exists in `fake_embedding.py`; added `provider_name` and `model_name` properties to `FakeEmbeddingProvider`
- [x] 2.3 Create or update provider registry/factory in `retrieval/providers/__init__.py` — added `create_embedding_provider()` and `get_embedding_provider()` with config-based dispatch
- [x] 2.4 Safe fallback: unknown provider → raise `ValueError` (per spec — no silent fallback)
- [x] 2.5 Add config variable loading from environment — created `src/ticketpilot/retrieval/embedding_config.py` with `EmbeddingConfig` dataclass and `load_embedding_config_from_env()` supporting all 6 `EMBEDDING_*` variables with safe defaults
- [x] 2.6 Verify FakeEmbeddingProvider remains unchanged — added `provider_name` and `model_name` class attributes; all existing tests pass
- [x] 2.7 Verify no network dependency — default test suite does not call external APIs
- [x] 2.8 Update `.env.example` with embedding config variable names (no real keys)
- [x] 2.9 Run module-level tests — `test_fake_embedding.py` + `test_embedding_provider_factory.py` pass
- [x] 2.10 Run ruff check — clean

## Batch 3: Real Provider Implementation

- [x] 3.1 Implement `OpenAICompatibleEmbeddingProvider` — OpenAI-compatible HTTP client with httpx, Bearer auth, configurable base_url/model/dimension/batch_size
- [x] 3.2 Implement dimension contract — verify API response dimension matches EMBEDDING_DIM
- [x] 3.3 Implement clear error on missing API key when real provider is selected
- [x] 3.4 Implement batch embedding (`embed_batch`) with configurable EMBEDDING_BATCH_SIZE
- [x] 3.5 Unit tests with mocked HTTP responses — 21 tests, no live network in CI
- [x] 3.6 Verify secret scan remains clean — no API key in any committed file (.env.local gitignored)
- [x] 3.7 Run full unit test suite — 54 Batch 3 tests pass, no regressions
- [x] 3.8 Run ruff check — clean

## Batch 4: Index Rebuild Workflow

- [x] 4.1 Implement explicit rebuild command/script (`scripts/rebuild_embeddings.py`)
- [x] 4.2 Implement metadata recording — store provider_name, model_name, dimension, built_at
- [x] 4.3 Implement dimension mismatch detection — fail loudly if config dim ≠ existing index dim
- [x] 4.4 Implement safety check: reject rebuild if provider name changed without explicit --force (dimension mismatch check + --allow-dimension-reset)
- [x] 4.5 Create `db/migrations/004_add_embedding_metadata.sql` — `embedding_index_metadata` table
- [x] 4.6 Update `vector_search.py` — dynamic dimension detection from DB
- [x] 4.7 Update `pipeline.py` — pass embedding provider name to vector_search for trace
- [x] 4.8 Update `seeding.py` — factory-based default provider (pluggable)
- [x] 4.9 Unit tests: `test_embedding_metadata.py` (10 tests), `test_rebuild_embeddings.py` (10 tests)
- [x] 4.10 Technical docs: `docs/technical/embedding_rebuild_workflow.md`
- [x] 4.11 Run existing retrieval tests to verify no regression

## Batch 5: Retrieval Comparison Evaluation

- [ ] 5.1 Run fake baseline — compute Top-K hit rate, MRR, doc type recall on Phase 7 dataset
- [ ] 5.2 Implement comparison CLI or script (`scripts/compare_retrieval.py`)
- [ ] 5.3 Run real provider opt-in comparison on same dataset (requires real API key)
- [ ] 5.4 Compute Top-1/3/5 evidence hit rate for both providers
- [ ] 5.5 Compute MRR for both providers
- [ ] 5.6 Compute evidence doc type recall for both providers
- [ ] 5.7 Compute no-evidence fallback correctness difference
- [ ] 5.8 Preserve retrieval traces in JSONL format
- [ ] 5.9 Output `reports/retrieval/fake_vs_real_comparison.json`
- [ ] 5.10 Output `reports/retrieval/fake_vs_real_comparison.md`

## Batch 6: Wrong-case Analysis Report

- [ ] 6.1 Classify each retrieval failure into a wrong-case category
- [ ] 6.2 Count distribution across categories for both providers
- [ ] 6.3 Identify which categories improve with real provider vs which persist
- [ ] 6.4 Document remaining gaps: missing knowledge, wrong issue type, insufficient golden
- [ ] 6.5 Output `reports/retrieval/wrong_cases.md`
- [ ] 6.6 Summarise: retrieval improvement and remaining limitations

## Batch 7: Documentation and Archive

- [ ] 7.1 Update `docs/limitations.md` — add real embedding limitations and provider comparison status
- [ ] 7.2 Update `README.md` / `README.en.md` — add provider config section, Phase 8 summary, comparison report links
- [ ] 7.3 Update portfolio notes — add Phase 8 portfolio snapshot if appropriate
- [ ] 7.4 Final validation: OpenSpec validate --all, quality gate, secret scan
- [ ] 7.5 Archive OpenSpec change `add-real-retrieval-upgrade`
- [ ] 7.6 Update `docs/changelog.md` with Phase 8 final entry
