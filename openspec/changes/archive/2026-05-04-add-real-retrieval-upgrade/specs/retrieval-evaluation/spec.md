## ADDED Requirements

### Requirement: Fake-vs-real comparison on Phase 7 dataset
The system SHALL support running retrieval evaluation with both FakeEmbeddingProvider and RealEmbeddingProvider on the identical Phase 7 dataset (101 eval tickets, 95 knowledge records).
The comparison SHALL use the same query construction and RRF fusion logic — only the embedding provider differs.

#### Scenario: Fake baseline run
- **GIVEN** FakeEmbeddingProvider is active
- **WHEN** retrieval evaluation runs on the Phase 7 dataset
- **THEN** results are saved with provider_name="fake" in the output

#### Scenario: Real provider comparison run
- **GIVEN** RealEmbeddingProvider is active (opt-in config)
- **WHEN** retrieval evaluation runs on the Phase 7 dataset
- **THEN** results are saved with provider_name matching the real provider

### Requirement: Top-K evidence hit rate
The comparison SHALL compute Top-1, Top-3, and Top-5 evidence hit rates.
A hit is counted when a golden-expected evidence document appears in the top-K retrieved results.

#### Scenario: Top-K hit rate computed
- **GIVEN** retrieval results for a query with expected doc IDs
- **WHEN** hit rate is calculated
- **THEN** Top-1, Top-3, and Top-5 hit rates are reported per query and aggregated

### Requirement: MRR (Mean Reciprocal Rank)
The comparison SHALL compute Mean Reciprocal Rank across all queries.
For each query, reciprocal rank = 1/rank(first_expected_doc). MRR = mean of all reciprocal ranks.

#### Scenario: MRR computed
- **GIVEN** retrieval results across all queries
- **WHEN** MRR is calculated
- **THEN** a single MRR value is reported for each provider

### Requirement: Evidence doc type recall
The comparison SHALL compute evidence doc type recall: the proportion of expected doc types (FAQ/Policy/Case) that appear in the retrieved set per query.
This mirrors the existing Phase 7 evaluation metric for apples-to-apples comparison.

#### Scenario: Doc type recall computed
- **GIVEN** a query with expected doc_types=["FAQ", "Policy"]
- **WHEN** doc type recall is calculated
- **THEN** it reports the fraction of expected types found in retrieved results

### Requirement: Expected doc ID hit rate (if golden supports it)
If golden expectations contain expected_doc_ids, the comparison SHALL compute expected doc ID hit rate.
If golden expectations do not contain expected_doc_ids, this metric SHALL be documented as "not available — golden lacks per-doc-ID targets."

#### Scenario: Doc ID hit rate conditional
- **GIVEN** golden expectations with expected_doc_ids
- **WHEN** doc ID hit rate is calculated
- **THEN** it reports the proportion of expected IDs found in top-K results

### Requirement: No-evidence fallback correctness
The comparison SHALL evaluate whether the fallback_required decision matches the golden expectation, and whether a real provider reduces unnecessary fallbacks.

#### Scenario: Fallback correctness compared
- **GIVEN** both fake and real provider results
- **WHEN** fallback correctness is compared
- **THEN** the difference in fallback rate between providers is reported

### Requirement: Retrieval trace preservation
Each query SHALL preserve a retrieval trace containing: query text, constructed keyword query, constructed vector query, top-K results per provider, fusion scores, and per-doc metadata.
Traces SHALL be saved in JSONL format for per-query analysis.

#### Scenario: Retrieval trace saved
- **GIVEN** a retrieval evaluation run
- **WHEN** the run completes
- **THEN** a JSONL file with per-query traces is saved to reports/retrieval/

### Requirement: Wrong-case analysis
The comparison SHALL produce a wrong-case analysis report categorising retrieval failures.
Each failed query SHALL be assigned at least one wrong-case category.

#### Scenario: Wrong cases categorised
- **GIVEN** queries where retrieval fails to surface expected evidence
- **WHEN** wrong-case analysis runs
- **THEN** each case is assigned to a category (keyword_mismatch, semantic_drift, missing_knowledge, wrong_issue_type, risk_not_reflected, doc_type_mismatch, insufficient_golden, fake_embedding_limit, real_embedding_overgeneralization)

### Requirement: Wrong-case categories defined
The wrong-case analysis SHALL use the following category definitions for classifying retrieval failures.

#### Scenario: Wrong-case categories used in analysis
- **GIVEN** a retrieval failure is detected
- **WHEN** the failure is classified
- **THEN** it SHALL be assigned to exactly one of the defined categories

| Category | Definition |
|----------|------------|
| keyword_mismatch | Query terms don't match knowledge record terms; FTS fails |
| semantic_drift | Embedding captures wrong semantics; top vectors are irrelevant |
| missing_knowledge | Expected evidence is not in the knowledge base |
| wrong_issue_type | Query classified to wrong issue type → wrong retrieval query |
| risk_not_reflected | Query contains risk signal but retrieval query doesn't encode it |
| doc_type_mismatch | Retrieved docs exist but wrong type (e.g., FAQ instead of Policy) |
| insufficient_golden | Golden expectation lacks specific doc ID targets — cannot measure precisely |
| fake_embedding_limit | Fake vector similarity is random; relevant docs drown in noise |
| real_embedding_overgeneralization | Real embedding retrieves broadly but misses precise match |

### Requirement: Report output paths
The comparison evaluation SHALL output to the specified paths.

#### Scenario: Comparison report written
- **GIVEN** a completed comparison evaluation run
- **WHEN** the run finishes
- **THEN** the following files SHALL exist:

| Artifact | Path |
|----------|------|
| Comparison metrics (JSON) | `reports/retrieval/fake_vs_real_comparison.json` |
| Comparison report (MD) | `reports/retrieval/fake_vs_real_comparison.md` |
| Wrong-case analysis (MD) | `reports/retrieval/wrong_cases.md` |
| Retrieval traces (JSONL) | `reports/retrieval/retrieval_traces.jsonl` |

### Requirement: No production benchmark claim
All comparison reports SHALL include a disclaimer:

> "This comparison uses synthetic data (101 eval tickets, 95 knowledge records) and does not represent real-world retrieval performance. Results are valid for relative comparison between embedding providers on this dataset only."

#### Scenario: Disclaimer present
- **GIVEN** a comparison report
- **WHEN** inspected
- **THEN** it includes the disclaimer text
