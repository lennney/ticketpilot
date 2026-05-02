# Proposal: Add Evaluation Pipeline

## Executive Summary

TicketPilot currently processes a raw Chinese ticket through intake normalization, intent classification, risk assessment, layered knowledge retrieval, evidence candidate collection, and evidence-grounded draft generation, then presents the result in a Streamlit human review console. However, there is no mechanism to measure how well the system performs. The team cannot answer basic questions: What fraction of tickets are classified correctly? How often does the risk assessor miss a high-risk flag? What proportion of draft citations are valid? How often does the unsupported-claim guard fire correctly?

This change adds an offline evaluation pipeline that quantifies TicketPilot behavior against a small, deterministic golden evaluation dataset. The evaluation runner loads tickets from a CSV, processes them through the existing pipeline (or individual stages), compares outputs against golden expectations, and produces a structured report with per-metric scores. Every metric is clearly documented with its definition, calculation method, and known limitations.

The pipeline is designed for determinism and reproducibility: the same evaluation data always produces the same report. No real embedding provider, no real LLM provider, no API keys, and no external services are required. The fake embedding limitation is clearly documented so that future evaluators understand the gap between measured performance and real-world performance.

## Problem Statement

Without an evaluation pipeline, TicketPilot has seven gaps:

1. **No objective quality measurement**: The team has no quantitative signal about whether the system is improving or regressing between changes. Feature additions are evaluated by manual demo rather than metric-based comparison.

2. **No regression detection**: A change that breaks intent classification for "refund" tickets or causes the risk assessor to miss all LEGAL_RISK flags goes undetected until a human notices during demo or review.

3. **No evidence retrieval quality signal**: The retrieval module produces ranked evidence candidates, but there is no recall@k or similar metric to measure whether the right documents are being retrieved.

4. **No draft quality measurement**: The draft generation produces replies with citations, but there is no automated check of whether citations are valid or whether the draft correctly handles no-evidence and high-risk cases.

5. **No guard behavior verification**: The unsupported-claim guard (CitationValidator) and the must_human_review trigger are tested at the unit level but never evaluated end-to-end on realistic ticket scenarios.

6. **No human-review decision readiness check**: The review console produces ReviewDecision JSONL records, but there is no evaluation of whether the system state at review time is correct (e.g., appropriate draft confidence, proper citation structure, correct guard flags).

7. **No benchmark for future improvements**: When real embedding providers or real LLM providers are added later, there will be no baseline to compare against. The evaluation pipeline establishes that baseline now, using fake providers, so that future changes can demonstrate measurable improvement.

## Proposed Solution

Add an offline evaluation pipeline consisting of:

1. **Evaluation dataset** (data/eval/tickets_eval.csv): A small CSV of seed tickets covering each intent class, each risk category, edge cases (empty text, very long text), and known-problem scenarios.

2. **Golden expectations** (data/eval/golden_expectations.csv): A CSV mapping each ticket to its expected intent, risk flags, severity, must_human_review value, expected evidence doc IDs, expected citation status, and expected draft fallback behavior.

3. **Evaluation runner** (scripts/run_eval.py): A standalone Python script that loads the dataset, runs each ticket through the pipeline (or individual module under test), compares against golden expectations, computes metrics, and writes a report.

4. **Reusable evaluation logic** (src/ticketpilot/evaluation/): If evaluation logic needs to be shared between the runner and tests, it lives in a new ticketpilot.evaluation module with clean abstractions.

5. **Unit and integration tests**: Standard test files that verify the evaluation pipeline itself is correct (e.g., metrics calculation is accurate, CSV loading handles edge cases, report format is valid).

6. **Documentation**: Clear documentation of what each metric means, how it is calculated, and what its limitations are (especially the fake embedding limitation).

### What This Change Does NOT Do

- Does not add a real embedding provider (stays with fake embeddings).
- Does not add a real LLM provider (stays with fake draft provider).
- Does not modify any existing src/ticketpilot/ production code.
- Does not modify any existing tests/ files.
- Does not modify retrieval, risk, drafting, review console, or pipeline behavior.
- Does not create a large evaluation dataset (starts small and deterministic).
- Does not claim real-world performance.
- Does not weaken the quality gate or treat skipped integration tests as passing.

## Why This Matters

1. **Objective quality baseline**: The team can point to a specific metric value (e.g., "intent accuracy: 87.5%") rather than qualitative assessment.

2. **Regression protection**: Every future change must pass the evaluation at least as well as the current baseline, preventing silent regressions.

3. **Measurable improvement path**: Future changes that add real embeddings or real LLMs can demonstrate improvement over the fake-provider baseline.

4. **Clear limitations documentation**: The gap between fake-provider evaluation and real-world performance is transparently documented, preventing overconfidence in the numbers.

5. **Test doubles for evaluation itself**: The evaluation pipeline is tested like any other module, ensuring the metrics are correct and the runner is reliable.

## Scope

### In Scope

- data/eval/tickets_eval.csv with 15-25 seed tickets
- data/eval/golden_expectations.csv with golden labels for each ticket
- scripts/run_eval.py evaluation runner script
- src/ticketpilot/evaluation/ module for reusable evaluation logic (if needed)
- Metric definitions: intent accuracy, risk recall/precision, severity correctness, must_human_review trigger accuracy, evidence recall@k, citation validity rate, draft fallback correctness, unsupported-claim guard behavior, human-review decision readiness
- Structured report output (JSON or JSONL)
- Determinism: same input always produces identical report
- Unit tests for evaluation logic (metrics, CSV loading, report generation)
- Integration tests for the full evaluation pipeline
- Technical documentation of the evaluation pipeline, metrics, and limitations
- Changelog and phase status update

### Out of Scope

- Real embedding provider (fake embeddings only; limitation documented)
- Real LLM provider (fake draft provider only; limitation documented)
- Large evaluation dataset (15-25 tickets only; limitation documented)
- Modifications to any existing src/ticketpilot/ production code
- Modifications to any existing tests/ files
- Changes to retrieval, risk, drafting, review console, or pipeline behavior
- Real-world performance claims of any kind
- Auto-send or auto-evaluation in production
- Performance benchmarking (latency, throughput)
- Integration with external eval frameworks (Langfuse, Ragas, DeepEval)
- CI/CD integration (running eval in CI is a future concern)
- Dashboard or visualization of evaluation results
- Continuous evaluation on live data
