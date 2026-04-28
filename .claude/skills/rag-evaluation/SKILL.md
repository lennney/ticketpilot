---
name: rag-evaluation
description: Use when modifying retrieval, chunking, RRF, rerank, citation, answer grounding, or evaluation scripts.
---

# RAG Evaluation

Required metrics:
- Recall@3
- Recall@5
- MRR
- citation correctness
- evidence support rate
- unsupported claim rate

Rules:
1. Do not use vector-only retrieval for the MVP.
2. Keep FAQ, Policy, and Case source types visible in retrieval outputs.
3. Retrieval trace must preserve query, keyword results, vector results, fused results, final evidence, scores, doc_type, and source ids.
4. Do not claim improvement without running evaluation.
