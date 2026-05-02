## Context

TicketPilot is a Chinese customer support ticket triage and evidence-grounded reply Copilot. The existing pipeline processes a raw Chinese ticket through intake normalization, intent classification, risk assessment, layered knowledge retrieval, evidence candidate collection, and evidence-grounded draft generation, then presents the result in a Streamlit human review console. The system uses fake embeddings for vector search and a fake draft provider for reply generation -- no real AI providers are called.

**Current state**: All six pipeline stages are implemented. The Streamlit review console is operational. ReviewDecision JSONL persistence is in place. Development trace, technical docs, portfolio docs, skills docs, and prompt library are documented. OpenSpec active changes = 0, openspec validate --all passed, quality gate passed, 0 skipped integration tests.

**Constraints**:
- MUST NOT modify src/ticketpilot/ production code
- MUST NOT modify tests/ files
- MUST NOT add real embedding provider
- MUST NOT add real LLM provider
- MUST NOT create a large evaluation dataset
- MUST NOT weaken the quality gate
- MUST NOT treat skipped integration tests as passing
- MUST NOT require API keys or external services
- MUST use small deterministic evaluation data
- MUST document fake embedding limitation clearly
- MUST measure current system behavior, not hide weak results
- State of this change is planning (not yet proposed)

## Goals / Non-Goals

**Goals:**
- Evaluation dataset (data/eval/tickets_eval.csv) with 15-25 seed tickets spanning all intents, risk categories, and edge cases
- Golden expectations (data/eval/golden_expectations.csv) mapping each ticket to expected outputs
- Evaluation runner script (scripts/run_eval.py) that loads data, runs pipeline, compares outputs, computes metrics, writes report
- Reusable evaluation logic module (src/ticketpilot/evaluation/) for metrics, comparison, and report generation
- Nine metric categories: intent accuracy, risk flag recall/precision, severity correctness, must_human_review trigger accuracy, evidence recall@k, citation validity rate, draft fallback correctness, unsupported-claim guard behavior, human-review decision readiness
- Structured report output (JSON) with per-metric scores, per-ticket details, and summary
- Deterministic: same input always produces identical report
- Unit tests: metrics calculation, CSV loading, report generation, comparison logic
- Integration tests: full pipeline evaluation, edge cases, determinism
- Technical documentation: evaluation pipeline, metric definitions, limitations
- Changelog and phase status update

**Non-Goals:**
- Real embedding provider (fake embeddings remain; limitation documented)
- Real LLM provider (fake draft provider remains; limitation documented)
- Large evaluation dataset (15-25 tickets documented as insufficient for statistical significance)
- Modifications to src/ticketpilot/ production code
- Modifications to existing tests/ files
- Changes to retrieval, risk, drafting, review console, or pipeline behavior
- Real-world performance claims
- Auto-send or auto-evaluation
- Performance/latency benchmarking
- CI/CD integration
- Dashboard/visualization
- Continuous evaluation on live data
- Integration with Langfuse, Ragas, DeepEval, or any external eval framework

## Architecture Diagram

```
data/eval/tickets_eval.csv
  |
  v
data/eval/golden_expectations.csv
  |
  v
scripts/run_eval.py
  |
  +---> Load tickets + golden expectations
  |
  +---> For each ticket:
  |       |
  |       +---> Run through TicketPilot pipeline
  |       |       (intake -> classification -> risk -> retrieval
  |       |        -> evidence -> draft)
  |       |
  |       +---> Compare against golden expectations
  |       |       (per-metric comparison functions)
  |       |
  |       +---> Accumulate per-ticket results
  |
  +---> Compute aggregate metrics
  |
  +---> Write eval_report.json
  |
  v
eval_report.json
  - summary: { metric_name: { value, total, correct, ... } }
  - per_ticket: [ { ticket_id, results: { ... } } ]
  - metadata: { timestamp, dataset_info, constraints, limitations }
```

## Evaluation Dataset Schema

### tickets_eval.csv

| Column | Type | Description |
|--------|------|-------------|
| ticket_id | str | Unique identifier |
| raw_text | str | Raw Chinese ticket text |
| expected_intent | str | Expected intent label |
| expected_risk_flags | str | Pipe-delimited risk flags (e.g., LEGAL_RISK|COMPLAINT_RISK) |
| expected_severity | str | Expected severity: HIGH, MEDIUM, LOW |
| expected_must_human_review | bool | Whether human review should be required |
| expected_evidence_doc_ids | str | Pipe-delimited expected doc IDs that should be retrieved |
| expected_citations_valid | bool | Whether draft citations should all be valid |
| expected_fallback | str | Expected fallback type: none, no_evidence, high_risk, generation_error |
| expected_unsupported_claims | bool | Whether unsupported claims are expected |
| notes | str | Free-text notes about this ticket |

### golden_expectations.csv

Same schema as tickets_eval.csv but with expected_* columns only (no raw_text). The two files are joined on ticket_id. This separation allows the expectations to be versioned independently from the ticket text (e.g., when updating labels without changing input text).

**Design decision**: Merge into a single CSV (tickets_eval.csv) if the number of columns remains manageable. Split into two files if the per-ticket metadata grows large. For MVP (15-25 tickets), a single CSV is simpler and preferred unless the design explicitly demands two files.

## Metric Definitions

### 1. Intent Classification Accuracy

- **Definition**: Fraction of tickets where classification.intent matches expected_intent.
- **Calculation**: correct / total where correct counts exact string match.
- **Range**: [0.0, 1.0]
- **Limitations**: Exact string match penalizes near-misses. Intent labels must match golden set exactly.

### 2. Risk Flag Recall / Precision

- **Definition**: For each risk flag type (LEGAL_RISK, COMPLAINT_RISK, ACCOUNT_SECURITY, INSUFFICIENT_EVIDENCE, etc.), compute recall (fraction of expected flags that appear in output) and precision (fraction of output flags that were expected).
- **Calculation**:
  - recall = |expected_flags & actual_flags| / |expected_flags| (0 if expected is empty)
  - precision = |expected_flags & actual_flags| / |actual_flags| (1 if actual is empty)
  - Macro-averaged across all tickets.
- **Range**: [0.0, 1.0] for each.
- **Limitations**: Flag naming must be consistent. Currently risk assessment uses flag strings from RiskFlag enum.

### 3. Severity Correctness

- **Definition**: Fraction of tickets where risk_assessment.severity matches expected_severity.
- **Calculation**: correct / total.
- **Range**: [0.0, 1.0]
- **Limitations**: Severity is a simple LOW/MEDIUM/HIGH enum. The current rule-based assessor uses keyword patterns.

### 4. must_human_review Trigger Accuracy

- **Definition**: Fraction of tickets where risk_assessment.must_human_review matches expected_must_human_review.
- **Calculation**: correct / total.
- **Range**: [0.0, 1.0]
- **Limitations**: Binary classification -- no partial credit.

### 5. Evidence Recall@k

- **Definition**: For each ticket, fraction of expected document IDs that appear in the top-k evidence candidates (k=1, 3, 5).
- **Calculation**: For each k in {1, 3, 5}, recall@k = |expected_doc_ids & actual_doc_ids[:k]| / |expected_doc_ids| (0 if expected is empty).
- **Range**: [0.0, 1.0] per k.
- **Limitations**: Heavily influenced by fake embeddings. Current fake embedding returns cosine similarity based on simple token overlap. Real embeddings would produce different rankings. This metric is primarily a regression check, not a real retrieval quality measure.

### 6. Citation Validity Rate

- **Definition**: Fraction of draft citations where the cited chunk ID actually exists in the retrieved evidence candidates and the evidence excerpt is non-empty.
- **Calculation**: valid_citations / total_citations across all tickets that produce drafts with citations.
- **Range**: [0.0, 1.0]
- **Limitations**: Only checks structural validity (chunk exists, excerpt non-empty). Does not verify semantic correctness of the claim-excerpt relationship.

### 7. Draft Fallback Correctness

- **Definition**: Fraction of tickets where the actual fallback type matches the expected fallback type.
- **Calculation**: correct / total.
- **Range**: [0.0, 1.0]
- **Limitations**: Fallback types are none (normal draft), no_evidence (empty evidence), high_risk (human review required), generation_error (provider exception). These match the internal DraftGenerationTrace.fallback_reason values.

### 8. Unsupported-Claim Guard Behavior

- **Definition**: Fraction of tickets where the presence/absence of unsupported claims in the draft matches expectation.
- **Calculation**: correct / total where correct means len(draft.unsupported_claims) > 0 == expected_unsupported_claims.
- **Range**: [0.0, 1.0]
- **Limitations**: The CitationValidator uses regex patterns that are imprecise (high false-positive/false-negative rate). This metric measures guard behavior, not actual claim support quality.

### 9. Human-Review Decision Readiness

- **Definition**: For tickets where a ReviewDecision would be produced (simulated in evaluation), verify that:
  - The decision final_intent matches expected intent (or the classification intent if no override).
  - The decision must_human_review flag matches the risk assessment flag.
  - The decision contains a timestamp.
- **Calculation**: Composite score: fraction of sub-checks that pass across all tickets.
- **Range**: [0.0, 1.0]
- **Limitations**: Since evaluation runs without a real review console session, this metric simulates the decision state. Real decision readiness depends on the Streamlit app state.


## Evaluation Runner Design

### scripts/run_eval.py

The runner is a standalone Python script that:

1. Load configuration: Parse optional CLI arguments (e.g., --output, --data-dir, --verbose).
2. Load dataset: Read tickets_eval.csv into a list of ticket records.
3. Load golden expectations: Read golden_expectations.csv (or from the same CSV if merged).
4. Process each ticket: For each ticket, call the full pipeline (or individual stage under evaluation) and collect outputs.
5. Compare outputs: Run each metric comparison function against golden expectations.
6. Aggregate results: Compute summary statistics across all tickets.
7. Write report: Write eval_report.json with summary, per-ticket details, and metadata.

### Reusable Evaluation Logic (src/ticketpilot/evaluation/)

If the comparison functions or metric calculations are useful outside the runner (e.g., in tests), they live in src/ticketpilot/evaluation/. Otherwise, they stay in the runner script.

Proposed module structure:

```
src/ticketpilot/evaluation/
    __init__.py            # Exports: run_evaluation, compare, metrics
    metrics.py             # Individual metric functions
    comparison.py          # Compare pipeline output to golden expectations
    report.py              # Report building and serialization
    loader.py              # CSV loading and validation
```

This module is tested independently by unit tests.

### Pipeline Invocation

The runner calls the existing pipeline entry points:

- intake_risk_pipeline(raw_text) for intake -> classification -> risk assessment
- run_retrieval(ticket_output) for evidence retrieval (indirectly via pipeline)
- generate_draft(ticket_output) for draft generation

These are the public API functions -- no internal functions are called directly. This ensures the evaluation measures real system behavior.

### Error Handling

- If a ticket fails to process (e.g., pipeline exception), the per-ticket result records the error and the metric contribution is marked as failed.
- The runner continues processing remaining tickets (no early exit on error).
- The report includes a failed_tickets list with error details.

## Output Report Format

The report is a JSON object with three top-level sections: metadata, summary, and per_ticket.

- **metadata**: timestamp, dataset filename, num_tickets, failed_tickets list, constraints dict (embedding_provider, draft_provider, real_embedding_limitation, real_llm_limitation, dataset_size_limitation)
- **summary**: A dict keyed by metric name (intent_accuracy, risk_flag_recall, risk_flag_precision, severity_correctness, must_human_review_accuracy, evidence_recall_at_1/3/5, citation_validity_rate, draft_fallback_correctness, unsupported_claim_guard_correctness, human_review_readiness). Each value is a dict with keys value (float), correct (int), total (int), error (int), and optional details.
- **per_ticket**: Array of per-ticket results, each with ticket_id, results dict, and errors list.

## Determinism and Reproducibility

1. **Deterministic data**: The evaluation CSV files are checked into version control and never modified by the evaluation run.

2. **Deterministic pipeline**: All pipeline components are deterministic:
   - Fake embeddings produce deterministic similarity scores.
   - Fake draft provider produces deterministic output.
   - Risk assessment rules are deterministic.
   - Intent classification rules are deterministic.

3. **Deterministic runner**: The runner processes tickets in CSV order, uses no randomness, and produces identical output for identical input.

4. **Reproducibility guarantee**: Given the same commit hash, the same evaluation data, and the same Python environment, scripts/run_eval.py produces byte-identical eval_report.json.

5. **Verification**: A test asserts that two consecutive runs produce identical output.


## Test Strategy

### Unit Tests

- **test_evaluation_metrics.py**: Tests each metric function in isolation:
  - Intent accuracy: exact match, case sensitivity, empty lists
  - Risk recall/precision: empty expected, empty actual, partial overlap, full overlap
  - Severity correctness: all three severity levels
  - must_human_review accuracy: true/false matching
  - Evidence recall@k: various k values, empty expected, empty results
  - Citation validity: all valid, some invalid, empty list
  - Draft fallback correctness: all fallback types
  - Unsupported claim guard correctness: expected true/false
  - Human-review readiness: composite score calculation

- **test_evaluation_loader.py**: Tests CSV loading:
  - Valid CSV loads correctly
  - Missing columns raise appropriate error
  - Empty file behavior
  - Whitespace trimming
  - Pipe-delimited field parsing

- **test_evaluation_report.py**: Tests report generation:
  - Report structure matches expected schema
  - Summary values computed correctly from per-ticket results
  - Metadata includes constraints and limitations
  - JSON serialization roundtrip

- **test_evaluation_comparison.py**: Tests comparison logic:
  - Full match produces correct per-ticket results
  - Partial match produces correct partial scores
  - Pipeline errors are recorded as failed
  - Missing golden expectation raises clear error

### Integration Tests

- **test_evaluation_pipeline.py**: End-to-end test:
  - Loads tickets_eval.csv and golden_expectations.csv from test fixtures
  - Runs full evaluation pipeline
  - Verifies report structure
  - Verifies summary contains all expected metrics
  - Verifies per-ticket results are populated
  - Verifies determinism (two runs produce identical report)

### Test Fixtures

- Small test CSV files with 2-3 tickets each (not the full eval dataset)
- Test golden expectations for those tickets
- Test output directory for report writing

### What NOT to Test

- Real embedding or LLM provider calls (out of scope)
- Pipeline behavior (tested by existing pipeline tests)
- Draft generation correctness (tested by existing drafting tests)
- Risk assessment rules (tested by existing risk tests)
- Review console UI behavior (out of scope)

## Limitations

### Critical: Fake Embedding Provider

The evaluation uses fake embeddings that compute cosine similarity based on simple token overlap between the ticket text and knowledge document text. This means:

1. **Evidence recall@k scores do not reflect real retrieval quality.** A score of 0.8 with fake embeddings does not imply 0.8 with real embeddings.
2. **Keyword overlap dominates results.** Tickets and documents sharing many keywords will score higher regardless of semantic relevance.
3. **Out-of-vocabulary handling is missing.** Fake embeddings have no concept of synonyms, paraphrases, or semantic similarity.

**Documented limitation**: All evaluation reports must include the disclaimer: "This evaluation uses fake embeddings (token-overlap cosine similarity). Evidential recall and citation scores do not reflect real-world performance. Real embedding provider evaluation is required before drawing conclusions about retrieval quality."

### Critical: Fake Draft Provider

The evaluation uses the FakeDraftProvider which constructs replies via template composition. This means:

1. **Citation validity rate is artificially high.** The fake provider always produces structurally valid citations (by construction).
2. **Draft quality metrics are meaningless for real-world performance.** Template-based replies are not representative of LLM-generated replies.
3. **Unsupported claim guard evaluation is a tautology.** The CitationValidator regex patterns detect what the fake provider (by construction) avoids.

### Critical: Small Dataset

The evaluation dataset contains 15-25 hand-crafted tickets. This means:

1. **Not statistically significant.** A single ticket result changes aggregate metrics by 4-7 percentage points.
2. **Not representative of real distribution.** Hand-crafted tickets do not reflect real ticket frequency, language variation, or edge case distribution.
3. **Overfitting risk.** The evaluation may inadvertently optimize for these specific tickets rather than general behavior.

### Additional Limitations

- **No semantic evaluation**: Metrics only check structural and label-based correctness. There is no evaluation of semantic quality, tone, or helpfulness.
- **No end-to-end workflow evaluation**: The pipeline is evaluated per-stage, not on the full human-review workflow including the Streamlit console.
- **Single language**: All tickets are Chinese. No multilingual evaluation.
- **No performance metrics**: Latency, throughput, and resource usage are not measured.
- **No adversarial evaluation**: The dataset does not include intentionally misleading or adversarial tickets.

## Deferred Real-Data / Real-Embedding Evaluation

The following items are explicitly deferred to a future change:

1. **Real embedding provider evaluation**: When a real embedding provider (e.g., OpenAI, sentence-transformers) is added, the evaluation pipeline should be run with the real provider and results compared against the fake baseline.

2. **Real LLM provider evaluation**: When a real LLM draft provider is added, the evaluation should include draft quality metrics (e.g., BLEU, ROUGE, BERTScore) and human preference comparisons.

3. **Large-scale evaluation dataset**: A dataset of 100+ real (or realistically synthetic) tickets should be constructed for statistical significance.

4. **Semantic evaluation metrics**: Metrics that measure semantic correctness, not just label match (e.g., embedding-based similarity for intent proximity).

5. **Cross-validated evaluation**: Train/test split evaluation for any learned components.

6. **Adversarial evaluation**: Test suite of edge cases designed to break the system.

7. **CI/CD integration**: Running the evaluation pipeline automatically on every PR or commit.

8. **Regression dashboard**: Historical tracking of metric values over time.

## Files to Create (Summary)

```
data/eval/
  tickets_eval.csv
  golden_expectations.csv

scripts/
  run_eval.py

src/ticketpilot/evaluation/
  __init__.py
  metrics.py
  comparison.py
  report.py
  loader.py

tests/unit/
  test_evaluation_metrics.py
  test_evaluation_loader.py
  test_evaluation_report.py
  test_evaluation_comparison.py

tests/integration/
  test_evaluation_pipeline.py

docs/technical/
  evaluation_pipeline.md  (new file)

docs/
  changelog.md  (update)
  phase_status.md  (update)
```
