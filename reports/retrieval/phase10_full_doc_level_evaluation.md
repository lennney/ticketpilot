# Retrieval Comparison Report

*Generated at 2026-05-06 03:54:06 UTC*

## Dataset

- Tickets: `data/eval/tickets_eval.csv`
- Golden expectations: `data/eval/golden_expectations.csv`
- Total cases: 101

## Configuration

- **eval_type**: full_doc_level
- **total_cases**: 101
- **p0_labeled_cases**: 86
- **mode**: full

## Aggregate Metrics

### Top-K Doc Type Hit Rate

| k | Hit Rate |
|---|----------|
| 1 | 96.0% |
| 3 | 96.0% |
| 5 | 96.0% |
| 10 | 96.0% |

### Top-K Doc ID Hit Rate

| k | Hit Rate |
|---|----------|
| 1 | 0.0% |
| 3 | 0.0% |
| 5 | 0.0% |
| 10 | 0.0% |

### Top-K P0 Added Record Hit Rate

| k | Hit Rate |
|---|----------|
| 1 | 0.0% |
| 3 | 0.0% |
| 5 | 0.0% |
| 10 | 0.0% |

### Mean Reciprocal Rank

| Metric | Value |
|--------|-------|
| MRR (doc_type) | 0.9604 |
| MRR (doc_id) | 0.0000 |

## Wrong Cases

### Failure Mode Distribution

| Failure Mode | Count |
|--------------|-------|
| missing_doc_type | 4 |

### Per-Case Details

- **case_edge_001** (missing_doc_type)
  - Hit pattern: @1:miss, @3:miss, @5:miss, @10:miss
  - RR (doc_type): 0.0000
  - Expected doc_types: [] | Retrieved: Policy(doc_policy_0018)@1, FAQ(doc_faq_0017)@2, Case(doc_case_0017)@3, FAQ(doc_faq_0006)@4, Policy(doc_policy_0005)@5, Policy(doc_policy_0020)@6, FAQ(doc_faq_0009)@7, FAQ(doc_faq_0013)@8, FAQ(doc_faq_0018)@9, Policy(doc_policy_0014)@10

- **case_edge_003** (missing_doc_type)
  - Hit pattern: @1:miss, @3:miss, @5:miss, @10:miss
  - RR (doc_type): 0.0000
  - Expected doc_types: [] | Retrieved: FAQ(doc_faq_0003)@1, Policy(doc_policy_0007)@2, Policy(doc_policy_0008)@3, Case(doc_case_0009)@4, Policy(doc_policy_0010)@5, Case(doc_case_0014)@6, FAQ(doc_faq_0013)@7, Case(doc_case_0006)@8, FAQ(doc_faq_0006)@9, Case(doc_case_0003)@10

- **case_edge_004** (missing_doc_type)
  - Hit pattern: @1:miss, @3:miss, @5:miss, @10:miss
  - RR (doc_type): 0.0000
  - Expected doc_types: [] | Retrieved: FAQ(doc_faq_0020)@1, Case(doc_case_0004)@2, FAQ(doc_faq_0005)@3, Policy(doc_policy_0011)@4, Policy(doc_policy_0014)@5, FAQ(doc_faq_0013)@6, Policy(doc_policy_0003)@7, FAQ(doc_faq_0011)@8, Case(doc_case_0020)@9, Policy(doc_policy_0016)@10

- **case_edge_005** (missing_doc_type)
  - Hit pattern: @1:miss, @3:miss, @5:miss, @10:miss
  - RR (doc_type): 0.0000
  - Expected doc_types: [] | Retrieved: Policy(doc_policy_0002)@1, FAQ(doc_faq_0008)@2, Policy(doc_policy_0008)@3, Policy(doc_policy_0015)@4, FAQ(doc_faq_0011)@5, Case(doc_case_0019)@6, FAQ(doc_faq_0009)@7, Policy(doc_policy_0018)@8, Case(doc_case_0018)@9, FAQ(doc_faq_0016)@10

## Doc-ID Wrong-Case Recheck

Of 4 wrong cases, 0 have an expected doc_id in top-10 results (reclassified from doc_type failure to doc_id hit).
