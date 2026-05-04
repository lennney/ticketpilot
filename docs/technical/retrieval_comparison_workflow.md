# Retrieval Comparison Workflow

This document describes the retrieval comparison tooling used to evaluate and compare
evidence retrieval quality across different embedding providers and configurations.

## Overview

The retrieval comparison workflow measures how well the retrieval pipeline finds relevant
evidence documents for each evaluation ticket. It computes:

- **Top-K hit rate** (doc_type level): whether at least one expected document type appears
  in the top-K retrieved results.
- **Top-K hit rate** (doc_id level): whether at least one expected document ID appears
  in the top-K retrieved results (requires `expected_relevant_doc_ids` in golden data).
- **Mean Reciprocal Rank (MRR)**: the average of `1 / rank(first_relevant)` across all cases.
- **Wrong-case classification**: categorizes retrieval failures into `missing_doc_type`
  (expected doc type never appears) or `below_top_10` (appears but outside top-10).

## Architecture

```
data/eval/
  golden_expectations.csv  ──┐
  tickets_eval.csv         ──┤
                              v
scripts/run_retrieval_comparison.py
    │
    ├── loaders.py        → EvalTicket, GoldenExpectation
    ├── retrieval_metrics.py → RetrievedDoc, RetrievalComparisonCase, metrics
    ├── retrieval_comparison.py → JSON + Markdown report builders
    │
    v
reports/retrieval/
  comparison_report.json
  comparison_report.md
```

## Data Structures

### RetrievedDoc
```python
@dataclass
class RetrievedDoc:
    doc_id: str       # Document UUID
    doc_type: str     # "FAQ", "Policy", or "Case"
    rank: int         # 1-based rank in retrieval results
    score: float      # Relevance score
```

### RetrievalComparisonCase
```python
@dataclass
class RetrievalComparisonCase:
    case_id: str                          # Matches golden expectations
    query: str                            # Search query used
    retrieved_docs: list[RetrievedDoc]    # Sorted by rank
    expected_doc_types: frozenset[str]    # From golden expectations
    expected_doc_ids: frozenset[str] | None  # Optional doc_id expectations
```

## Metric Definitions

### Top-K Hit Rate
```
hit_rate_at_k = count(cases_with_hit_at_k) / total_cases
```

A "hit" at k means at least one retrieved document within the top-k has an expected
doc_type (or doc_id, depending on the metric level).

### Mean Reciprocal Rank (MRR)
```
reciprocal_rank(case) = 1 / rank_of_first_relevant_doc
                       (0.0 if no relevant doc found)

MRR = sum(reciprocal_rank(case) for all cases) / total_cases
```

### Wrong-Case Classification

| Failure Mode | Description |
|---|---|
| `missing_doc_type` | None of the expected doc types appear in top-10 results |
| `below_top_10` | An expected doc type appears in results, but not within top-10 |

## CLI Usage

### Mock Mode (Batch 5A — no real pipeline calls)

```bash
uv run python scripts/run_retrieval_comparison.py \
    --tickets data/eval/tickets_eval.csv \
    --golden data/eval/golden_expectations.csv \
    --out-json reports/retrieval/comparison_report.json \
    --out-md reports/retrieval/comparison_report.md
```

Options:
- `--retrieval-mode mock|pipeline` — `mock` (default) generates synthetic results;
  `pipeline` runs the real retrieval pipeline (planned for Batch 5B).
- `--mock-seed N` — random seed for deterministic mock results (default: 42).

### Pipeline Mode (Batch 5B — requires real provider)

```bash
uv run python scripts/run_retrieval_comparison.py \
    --tickets data/eval/tickets_eval.csv \
    --golden data/eval/golden_expectations.csv \
    --retrieval-mode pipeline \
    --out-json reports/retrieval/comparison_report.json \
    --out-md reports/retrieval/comparison_report.md
```

## Report Output

### JSON Report Structure
```json
{
  "generated_at": "2026-05-05T...",
  "metadata": {
    "tickets_path": "data/eval/tickets_eval.csv",
    "golden_path": "data/eval/golden_expectations.csv"
  },
  "config": {
    "retrieval_mode": "mock",
    "mock_seed": 42
  },
  "total_cases": 96,
  "aggregate_metrics": {
    "hit_rate_doc_type": { "1": 0.75, "3": 0.88, "5": 0.93, "10": 0.97 },
    "mrr_doc_type": 0.6234,
    "hit_rate_doc_id": { ... },    // optional
    "mrr_doc_id": 0.5123           // optional
  },
  "per_case_results": {
    "case_refu_001": {
      "top_k_doc_type_hit": { "1": true, "3": true, "5": true, "10": true },
      "reciprocal_rank_doc_type": 1.0
    }
  },
  "wrong_cases": [
    {
      "case_id": "case_refu_015",
      "failure_mode": "missing_doc_type",
      "details": "Expected doc_types: [Policy] | Retrieved: FAQ(...)@1, FAQ(...)@2",
      "top_k_doc_type_hit": { "1": false, "3": false, ... },
      "reciprocal_rank_doc_type": 0.0
    }
  ],
  "wrong_case_count": 3
}
```

### Markdown Report Sections
1. **Dataset** — file paths and case count
2. **Configuration** — retrieval mode and parameters
3. **Aggregate Metrics** — hit rate tables and MRR
4. **Wrong Cases** — failure mode distribution and per-case details

## Golden Expectations: Doc ID Support

The `expected_relevant_doc_ids` column in `golden_expectations.csv` is optional.
When populated (semicolon-separated document IDs), the comparison computes doc_id-level
hit rates and MRR. When absent or empty, doc_id metrics are `null` in reports.

## Report Paths

| Report | Path |
|---|---|
| Comparison JSON | `reports/retrieval/comparison_report.json` |
| Comparison Markdown | `reports/retrieval/comparison_report.md` |

## Testing

```bash
# Unit tests for metric computation
uv run pytest tests/unit/test_retrieval_metrics.py -v --tb=short

# Unit tests for report builders
uv run pytest tests/unit/test_retrieval_comparison.py -v --tb=short

# All retrieval comparison tests (56 tests)
uv run pytest tests/unit/test_retrieval_metrics.py tests/unit/test_retrieval_comparison.py -v --tb=short
```
