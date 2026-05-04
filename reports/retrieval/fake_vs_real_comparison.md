# Fake vs Real Retrieval Comparison

*Generated at 2026-05-04 17:13:13 UTC*

## Dataset

- Total cases: 101
- Golden expectations: `data/eval/golden_expectations.csv`

## Providers

| Metric | Fake | Real |
|--------|------|------|
| File | `reports/retrieval/fake_retrieval_rows.json` | `reports/retrieval/real_retrieval_rows.json` |
| Generated | 2026-05-04T16:37:20.579469+00:00 | 2026-05-04T17:12:13.170624+00:00 |
| Cases | 101 | 101 |
| Embedding provider | fake | openai_compatible |

## Aggregate Metrics

### Top-K Doc Type Hit Rate

| k | Fake | Real | Delta |
|---|------|------|-------|
| 1 | 31.7% | 42.6% | +10.9% |
| 3 | 47.5% | 56.4% | +8.9% |
| 5 | 53.5% | 58.4% | +5.0% |
| 10 | 59.4% | 59.4% | 0.0% |

### Mean Reciprocal Rank

| Metric | Fake | Real | Delta |
|--------|------|------|-------|
| MRR (doc_type) | 0.4114 | 0.4913 | +0.0799 |
| MRR (doc_id) | N/A | N/A | N/A — golden file does not include doc-level labels |

## Wrong Cases

| Metric | Fake | Real |
|--------|------|------|
| Wrong cases | 41 | 41 |

### Failure Mode Distribution

| Failure Mode | Fake | Real |
|--------------|------|------|
| missing_doc_type | 41 | 41 |

## Limitations

doc_id Recall@K is not available because the current golden file 
does not include doc-level labels (`expected_relevant_doc_ids`). 
This metric will be available once doc-level golden labels are added.
