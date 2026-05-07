# TicketPilot Iteration Summary

> Consolidated summary of all phases. For detailed per-phase analysis, see archived snapshots in `reports/eval/`.

---

## Phase Overview

| Phase | Focus | Key Output |
|-------|-------|-----------|
| Phase 7 | MVP Data Foundation | 101 eval tickets, 106 knowledge records, evaluation pipeline |
| Phase 8 | Real Retrieval Upgrade | Fake vs Real embedding comparison, Top-1 +10.9% |
| Phase 9 | Knowledge Optimization | 11 P0 records added, Provider Identity Gate |
| Phase 10 | Retrieval Diagnosis | Doc-ID Recall@10 = 91.9%, 78% wrong cases reclassified |
| Phase 11 | LLM Draft Generation | Evidence-grounded draft, 8 safety layers |
| Phase 12 | Provider Comparison | Fake vs Real (DeepSeek) comparison, identical safety patterns |

---

## Phase 7: MVP Data Foundation

**One-liner:** Expanded evaluation dataset from 10 to 101 tickets and knowledge base from 36 to 106 records, built 3 demo scenarios, and established a deterministic offline evaluation pipeline.

### Key Metrics

| Metric | Before | After | Delta |
|--------|------:|-----:|:-----:|
| Eval tickets | 10 | **101** | +91 |
| Knowledge records | 36 | **106** | +70 |
| FAQ | 12 | **41** | +29 |
| Policy | 12 | **34** | +22 |
| Case | 12 | **31** | +19 |
| Demo scenarios | 0 | **3** | +3 |
| Quality gate tests | — | 642 unit / 119 integration | — |

---

## Phase 8: Real Retrieval Upgrade

**One-liner:** Compared fake embedding (384-d deterministic hash) vs real embedding (DashScope text-embedding-v4, 1024-d) for evidence retrieval. Real embedding improved Top-1 by +10.9% and MRR by +0.0799, but 41 wrong cases were identical under both — revealing that the bottleneck is knowledge coverage, not embedding quality.

### Key Metrics

| Metric | Fake (384-d) | Real (1024-d) | Delta |
|--------|-------------:|--------------:|:-----:|
| Top-1 hit rate | 31.7% | **42.6%** | +10.9% |
| MRR | 0.4114 | **0.4913** | +0.0799 |
| Top-10 hit rate | 59.4% | 59.4% | 0.0% |
| Wrong cases | 41 | 41 | 0 |

### Key Finding

41 wrong cases were identical under fake and real embeddings — all `missing_doc_type`. This revealed that the bottleneck was knowledge coverage, not embedding quality.

---

## Phase 9: Evaluation-Driven Knowledge Optimization

**One-liner:** Built an evaluation-driven loop to identify knowledge gaps, add targeted synthetic records, and measure retrieval impact — uncovering that fake embeddings can be directionally misleading, and that under real semantic retrieval, knowledge expansion shows measurable but incomplete improvement.

### Key Metrics

| Metric | Phase 8 Real | Phase 9 Real | Delta |
|--------|-------------:|-------------:|:-----:|
| Knowledge records | 95 | **106** | +11 |
| Top-1 hit rate | 42.6% | **44.6%** | +2.0% |
| MRR (doc_type) | 0.4913 | **0.4995** | +0.0082 |
| P0 added-record hit rate | — | **75.0%** | — |

### Key Findings

1. **Fake evaluation can be misleading**: Under fake embeddings, knowledge expansion regressed Top-1 by 5.0%. Under real embeddings, the same expansion improved Top-1 by 2.0%. This informed the Provider Identity Gate.

2. **Provider Identity Gate**: Discovered that `load_dotenv()` was never called, causing all environment variables to be ignored and all evaluations to silently fall back to fake provider. Built a gate to verify actual provider identity at runtime.

---

## Phase 10: Hybrid Retrieval Ranking Diagnosis

**One-liner:** Built a trace-first diagnosis pipeline that proved 78% of "wrong" retrieval cases are actually correct at the document level — the metric was too coarse, not the retrieval system failing — and established doc-ID granularity as the correct evaluation standard.

### Key Metrics

| Metric | Value | Significance |
|--------|------:|--------------|
| **Doc-ID Recall@10** | **91.9%** | Nearly all expected docs retrieved |
| Doc-Type Recall@10 | 59.4% | Old coarse metric |
| **Delta (Doc-ID − Doc-Type)** | **+32.5pp** | Metric granularity gap quantified |
| Wrong cases reclassified | 32/41 | **78.0%** were metric granularity |

### Key Finding

78% of wrong cases were reclassified as correct after switching from doc-type to doc-ID granularity. The correct document was retrieved, but the coarse metric couldn't see it.

---

## Phase 11: Evidence-Grounded LLM Draft Generation

**One-liner:** Built a deterministic evidence-grounded draft generation pipeline that constrains LLM output to retrieved evidence, validates citations and claims, detects forbidden promises, and propagates human review decisions — all without real API calls or network access.

### Key Architecture

- **FakeLLMProvider Default**: Like FakeEmbeddingProvider, this ensures CI/development works without API keys
- **8 Safety Layers**: CitationValidator, ClaimGuard, evidence grounding, human review gate
- **Opt-in Real LLM**: Requires `TICKETPILOT_LLM_PROVIDER=openai_compatible` in `.env.local`

### Safety Components

| Component | Purpose |
|-----------|---------|
| DraftPromptInput | Structured input with evidence |
| CitationValidator | Validates draft references correct documents |
| ClaimGuard | Detects forbidden promises and unsupported claims |
| DraftGenerationResult | Structured output with confidence scores |
| HumanReviewDecision | Audit trail for review operations |

---

## Phase 12: Provider Comparison

**One-liner:** Ran offline comparison on 25 fixture cases comparing FakeLLMProvider (template-based) vs OpenAICompatibleProvider (DeepSeek). Both providers produced identical human review trigger patterns — confirming that safety rules are provider-agnostic.

### Key Metrics

| Metric | FakeLLM | DeepSeek |
|--------|--------:|---------:|
| Cases evaluated | 25 | 25 |
| Citation validation passed | 25 | 25 |
| Claim guard passed | 25 | 25 |
| Human review triggers | Identical | Identical |

### Key Finding

Safety rules (CitationValidator, ClaimGuard) work identically under fake and real providers. This confirms that the safety architecture is provider-agnostic.

---

## Iteration Logic

```
Phase 7: Build data foundation + evaluation pipeline
    → Phase 8: Compare embeddings, discover bottleneck is knowledge coverage
        → Phase 9: Add knowledge, discover Provider Identity Gate bug
            → Phase 10: Diagnose metrics, discover 78% wrong cases are metric issues
                → Phase 11: Build LLM draft generation with safety layers
                    → Phase 12: Compare providers, confirm safety rules are provider-agnostic
```

---

## Current State

- **101** synthetic eval tickets
- **106** knowledge records (FAQ=41, Policy=34, Case=31)
- **642+** unit tests, **119+** integration tests
- **87%** code coverage
- **Doc-ID Recall@10 = 91.9%**
- **No-auto-send compliance = 100%** (architecture constraint)
- **Phase 12** (current): Provider comparison complete, Phase 13 planned

---

*Generated: 2026-05-07*
