# Retrieval Evaluation Skill

## Purpose

Review, assess, and document the retrieval architecture of a hybrid keyword + vector search system. This skill explains how to evaluate the mechanics of a retrieval pipeline (whether the components work correctly) without conflating it with semantic retrieval quality, which requires real embeddings and evaluation data that may not be available in a prototype or MVP.

## When to Use

- Designing or reviewing a hybrid retrieval architecture (keyword + vector search with RRF fusion)
- Assessing whether retrieval pipeline mechanics are correct (embedding generation, indexing, search, fusion)
- Documenting the limitations of fake embeddings or synthetic data
- Planning for future real embedding provider integration and evaluation pipeline
- Reviewing retrieval test coverage and quality gate results
- Do NOT use this skill to claim real retrieval quality or precision/recall when using fake embeddings only

## Required Inputs

- Retrieval architecture documentation (source modules, database schema, provider interfaces)
- Knowledge of the embedding provider (real or fake, dimension, algorithm)
- Integration test results against a live database
- Understanding of the document types and chunking strategy
- The quality gate script and its integration test skip-count guard behavior

## Allowed Scope

- Reviewing retrieval architecture: source tables, chunk table, index configuration, query construction
- Evaluating pipeline mechanics: embedding generation works, HNSW index creation succeeds, keyword and vector search return results, RRF fusion produces combined rankings
- Assessing evidence mapping: FusedResult to EvidenceCandidate conversion, source table derivation, rank preservation
- Documenting limitations: fake embeddings have no semantic meaning, seed data is synthetic, no evaluation metrics exist
- Planning deferred items: real embedding provider, evaluation pipeline, golden-answer test sets
- Reviewing integration test coverage for retrieval components

## Forbidden Scope

- Do NOT claim real semantic retrieval quality from fake embeddings
- Do NOT report precision, recall, mRR, NDCG, or any retrieval quality metrics without real embeddings
- Do NOT claim real enterprise data coverage from seed data (12 FAQ, 12 Policy, 12 Case is not representative)
- Do NOT claim evaluation pipeline exists (no golden-answer test sets, no automated metrics)
- Do NOT report RRF scores as meaningful quality indicators (scores are rank-combined, not absolute)
- Do NOT skip documentation of fake embedding limitations in any document that mentions retrieval
- Do NOT skip the deferred items list (real provider, evaluation harness, realistic data)

## Step-by-Step Procedure

1. **Review the retrieval architecture**
   - Identify the source of documents (knowledge tables: FAQ, Policy, Case)
   - Review chunking strategy (parent-child, chunk sizes, linkage)
   - Verify index configuration (HNSW: m=16, ef_construction=200, ef_search=100; FTS: GIN on simple config)
   - Review the query construction: is it combining ticket text, intent terms, and risk-flag terms?

2. **Assess the embedding provider**
   - Is it real or fake?
   - If fake: document the algorithm (SHA-256 seeded pseudo-random), dimension (384), and limitation (PIPELINE VERIFICATION ONLY, no semantic meaning)
   - Verify the provider implements the expected interface so a real provider can replace it later

3. **Evaluate pipeline mechanics**
   - Verify keyword search returns results (FTS with simple config + Chinese business term fallback)
   - Verify vector search returns results (pgvector HNSW, cosine distance)
   - Verify RRF fusion combines both rankers with k=60
   - Verify evidence mapping produces valid EvidenceCandidate objects
   - All of these verify pipeline mechanics only, not semantic quality

4. **Review evidence recall**
   - Check that the system retrieves evidence relevant to the ticket's intent and risk flags
   - Verify that empty evidence is handled (INSUFFICIENT_EVIDENCE flag, safe fallback)
   - Note: with fake embeddings, recall assessment is limited to "does the pipeline return any results?" not "are the results semantically relevant?"

5. **Document limitations**
   - Fake embedding: no semantic meaning, pipeline verification only
   - Seed data: synthetic, not real enterprise data (36 documents, 12 per type)
   - FTS config: simple (whitespace tokenizer) with Chinese keyword fallback
   - No evaluation pipeline: no golden-answer test sets, no precision/recall/mRR metrics
   - RRF scores: not absolute quality indicators

6. **Plan for real evaluation (deferred)**
   - Real embedding provider integration (small 384-d, quality 768-d)
   - Golden-answer test sets for retrieval scenarios
   - Precision/recall/mRR/NDCG metric implementation
   - Evaluation harness script

## Acceptance Checklist

- [ ] Retrieval architecture is documented with all parameters (index type, m, ef_construction, ef_search, distance, FTS config, k)
- [ ] Fake embedding limitation is clearly stated wherever retrieval is discussed
- [ ] Seed data limitation is clearly stated as synthetic
- [ ] No precision/recall/mRR metrics reported from fake embeddings
- [ ] No claim of real semantic retrieval quality
- [ ] No claim of evaluation pipeline existence
- [ ] Deferred items listed: real provider, evaluation pipeline, realistic data
- [ ] Integration test results document what was verified (mechanics) and what was not (quality)

## Common Failure Modes

- **Reporting RRF scores as meaningful quality**: RRF scores are rank-combined scores, not absolute relevance measures. A score of 0.02 for one result vs 0.01 for another does not mean one is "twice as relevant."
- **Confusing pipeline verification with real evaluation**: Passing tests with fake embeddings proves the pipeline works, not that real retrieval quality is acceptable. These are different claims and must be clearly distinguished.
- **Omitting the "pipeline verification only" label**: Every document that mentions embeddings must include this label. Omitting it creates the false impression that the system has real semantic retrieval.
- **Calling 36 synthetic documents "a knowledge base" without qualification**: It is a seed data set for demo and integration testing. "Enterprise knowledge base" implies a scale and data quality that does not exist.
- **Claiming evaluation pipeline exists**: If there are no golden-answer test sets, no metric scripts, and no evaluation harness, do not claim an evaluation pipeline exists. Document it as deferred.

## Reusable Claude Code Prompt Template

```
I need to review the retrieval architecture and evaluation status of this system.

Walk through:

1. **Architecture review**: What is the source table structure? Chunking strategy? Index configuration? Query construction?

2. **Embedding provider**: Is it real or fake? 
   - If fake: document the algorithm, dimension, and the limitation label "PIPELINE VERIFICATION ONLY — no semantic meaning"
   - If real: document the provider, dimension, and how to verify semantic quality

3. **Pipeline mechanics**: What does "passing" mean?
   - Keyword search returns results (with fallback for Chinese text)
   - Vector search returns results (sorted by cosine distance)
   - RRF fusion produces combined ranking
   - Evidence mapping produces valid output
   These verify mechanics, NOT semantic retrieval quality.

4. **Limitations documentation** (mandatory):
   - [ ] Fake embeddings labeled as pipeline verification only
   - [ ] Seed data labeled as synthetic
   - [ ] No evaluation pipeline claimed
   - [ ] No precision/recall/mRR metrics reported
   - [ ] Deferred items listed

Do NOT claim real semantic retrieval quality from fake embeddings.
Do NOT report precision/recall metrics that don't exist.
Do NOT claim evaluation pipeline exists.
```

## TicketPilot Example

TicketPilot's retrieval architecture was reviewed and documented with the following evaluation:

**Architecture**: Two-layer source tables (knowledge_faq, knowledge_policy, knowledge_case) + unified knowledge_chunks table. HNSW index with m=16, ef_construction=200, ef_search=100, cosine distance. FTS with simple config + 8-term Chinese business keyword LIKE fallback. RRF fusion with k=60.

**Embedding provider**: FakeEmbeddingProvider (SHA-256 seeded pseudo-random, 384-dim, PIPELINE VERIFICATION ONLY). The EmbeddingProvider protocol interface is ready for real providers.

**Pipeline mechanics verified** (55 integration tests):
- Keyword search returns FAQ, Policy, Case results with FTS and fallback
- Vector search returns results sorted by cosine distance
- RRF fusion correctly combines rankings
- Evidence mapping produces valid EvidenceCandidate objects with source_table derivation
- Full retrieval pipeline integration (query -> embedding -> search -> fusion -> output)

**What was NOT verified**:
- Semantic retrieval quality (requires real embedding provider)
- Meaningful relevance ranking (requires real embedding provider)
- Real-world precision or recall (requires evaluation pipeline with golden-answer test sets)

**Deferred items documented**:
- Real embedding provider (small 384-d and quality 768-d tiers)
- Realistic enterprise data pack (replaces 36-document synthetic seed)
- Retrieval evaluation harness with golden question-answer pairs
- BM25 or alternative keyword retrieval
- SourceRouter (intent-to-source routing)
