# Phase 9 Evaluation Mechanism

This document consolidates the evaluation methodology developed across Phase 9.
It defines what each evaluation mode can (and cannot) tell us about retrieval quality.

## Three Evaluation Modes

### 1. Fake Provider Evaluation — Pipeline Mechanics Only

**What it does:** Runs the full retrieval pipeline with deterministic random embeddings
(SHA-256 hash → fake 384-d vector). Document content has zero influence on ranking.

**Valid for:**
- Verifying the pipeline executes end-to-end (keyword search → vector search → RRF fusion)
- Checking data schemas, row counts, and export format
- Debugging deterministic retrieval behavior (same input always produces same output)
- Taxonomy analysis (wrong case categorization)

**NOT valid for:**
- Measuring Top-K / MRR improvements from knowledge changes
- Evaluating semantic relevance of new documents
- Portfolio or interview metrics claims
- Any conclusion about whether a knowledge expansion "worked"

**Phase 9 finding:** Fake evaluation produced a directionally misleading Top-1 delta
(-5.0%) while real evaluation showed the opposite (+2.0%). The vector-space noise
from adding 11 documents overwhelmed any signal.

### 2. Real Provider Evaluation — Semantic Impact Measurement

**What it does:** Runs the retrieval pipeline with a production embedding provider
(e.g., dashscope `text-embedding-v4`, 1024-dim). Document content directly influences
ranking through semantic similarity.

**Required for:**
- Measuring Top-K / MRR changes from knowledge expansion
- Added-record hit audits
- Determining whether a wrong case is fixable by knowledge additions
- Portfolio and interview metrics

**Precondition:** Provider identity gate must pass (see `provider_identity_gate.md`).

### 3. Added-Record Hit Audit — Measuring Whether New Records Surface

**Definition:** For each new knowledge record (P0 record), check whether it appears in
the top-10 retrieval results for its designated target queries.

**Method:**
1. Identify P0 records by UUID from seed files
2. Map each P0 record to its targeted wrong cases (from the gap map)
3. For each (record, case) pair, check if the record's UUID appears in `retrieved_docs[:10]`
4. Count hits / total pairs

**Phase 9 results:**

| Provider | Hits | Interpretation |
|----------|------|---------------|
| Fake | 3/16 (18.8%) | Coincidental — vector-space proximity, not semantic |
| Real | 12/16 (75.0%) | Semantic relevance drives ranking |

**Limitation:** A hit does not mean the wrong case is fixed. The case may still fail
because another expected doc type remains missing from top-10. In Phase 9, 12 P0
records hit their targets, but 0 wrong cases were fixed because the targeted cases
were already passing under Phase 8 real (the required doc types were already present).

## Why Doc-Type-Level Wrong Cases Are Insufficient

The current golden file (`golden_expectations.csv`) labels each case with
`expected_evidence_doc_types` (e.g., `Policy;Case`). A case is "wrong" if any expected
type is missing from the top-10 results.

This metric cannot distinguish between:
- A new record replacing an old record of the same type (ranking improvement, same wrong-case count)
- A new record filling a genuine type gap (wrong case fixed)
- A new record hitting top-10 but not fixing the case (partial hit)

**Remedy:** Add `expected_relevant_doc_ids` to the golden file — per-case lists of
specific document IDs that should appear in results. This enables doc_id Recall@K,
which directly measures whether specific knowledge records are being retrieved.

## Hybrid Retrieval Three-Layer Diagnosis

When a wrong case persists, diagnose across three layers:

### Layer 1: Keyword Recall
- Does the query's extracted keywords match any document content?
- If not: query expansion gap — the knowledge exists but keywords don't reach it
- Fix: improve keyword extraction, add synonyms, or add query → document keyword mappings

### Layer 2: Vector Recall
- Does the semantic embedding rank relevant documents highly?
- If not: semantic gap — the document exists but its embedding is far from the query
- Fix: improve document content quality, add domain-specific terminology, or fine-tune embeddings

### Layer 3: RRF Fused Ranking
- Do relevant documents survive the RRF fusion?
- If keyword and vector both recall the document but RRF drops it: fusion weight gap
- Fix: tune RRF k parameter or keyword/vector weights

### Diagnostic Approach

```
For each wrong case:
  1. Check if expected doc_type appears in keyword-only results (top-20)
  2. Check if expected doc_type appears in vector-only results (top-20)
  3. Check if expected doc_type appears in RRF-fused results (top-10)
  4. Identify which layer drops the relevant document
```

This three-layer diagnosis was designed in Phase 9 but not yet automated. It is the
recommended next step for wrong-case resolution.
