# Phase 12 Case Studies

**Scope**: Local demo / portfolio prototype — offline fixture-based case studies
**Source**: `reports/eval/phase12_llm_provider_comparison_rows.json`

---

## Case Selection

Five representative cases selected from the 25-case Phase 12 fixture set, covering diverse scenarios:
- ordinary product consulting
- refund
- privacy risk
- legal complaint
- insufficient evidence / safe fallback

---

## Case 1: p12_001 — Ordinary Product Consulting

**Scenario**: A customer asks about product specifications.

| Field | Value |
|-------|-------|
| Case ID | p12_001 |
| Scenario | ordinary_product_consulting |
| Risk flags | none |
| Severity | LOW |
| Fake confidence | 0.85 |
| Fake human review | false |
| Fake has citations | true |
| Real confidence | 0.70 |
| Real human review | false |
| Real has citations | true |
| Real API error | false |

**What this case demonstrates**: Routine product consulting is low-risk and does not trigger human review under current rules. Both providers produced draft replies with citations and no human review triggers. The confidence difference (0.85 vs 0.70) reflects different confidence computation methods — not a quality difference.

---

## Case 2: p12_003 — Refund

**Scenario**: A customer requests a refund for a recent order.

| Field | Value |
|-------|-------|
| Case ID | p12_003 |
| Scenario | refund |
| Risk flags | compensation_risk (from fixture design) |
| Severity | MEDIUM or HIGH (compensation_risk present) |
| Fake confidence | 0.85 |
| Fake human review | false |
| Fake has citations | true |
| Real confidence | 0.70 |
| Real human review | false |
| Real has citations | true |
| Real API error | false |

**What this case demonstrates**: Refund cases with compensation signals are handled. The human review trigger depends on the specific fixture design. The draft is citation-grounded. The confidence score does not reflect whether the draft actually addressed the refund request correctly — only that the pipeline produced output.

---

## Case 3: p12_011 — Privacy Risk

**Scenario**: A customer reports a data privacy concern.

| Field | Value |
|-------|-------|
| Case ID | p12_011 |
| Scenario | privacy_risk |
| Risk flags | privacy_risk |
| Severity | HIGH |
| Fake confidence | 0.85 |
| Fake human review | **true** |
| Fake has citations | true |
| Real confidence | 0.70 |
| Real human review | **true** |
| Real has citations | true |
| Real API error | false |

**What this case demonstrates**: Privacy risk cases correctly trigger human review in both providers. This is the key safety property — high-risk outputs do not proceed automatically. Human review is forced regardless of confidence level. Both providers show identical human review triggers, confirming the risk rule is provider-agnostic.

---

## Case 4: p12_015 — Legal Complaint

**Scenario**: A customer threatens legal action.

| Field | Value |
|-------|-------|
| Case ID | p12_015 |
| Scenario | legal_complaint |
| Risk flags | legal_risk |
| Severity | HIGH (legal_risk always HIGH) |
| Fake confidence | 0.85 |
| Fake human review | **true** |
| Fake has citations | true |
| Real confidence | 0.70 |
| Real human review | **true** |
| Real has citations | true |
| Real API error | false |

**What this case demonstrates**: Legal complaint cases (e.g., threats of legal action) trigger HIGH severity and force human review. This is an intentional design choice — legal risk should never be handled by auto-send. The draft is citation-grounded but requires human judgment before any action.

---

## Case 5: p12_019 — Insufficient Evidence

**Scenario**: A ticket with limited retrievable evidence.

| Field | Value |
|-------|-------|
| Case ID | p12_019 |
| Scenario | evidence_insufficient |
| Risk flags | insufficient_evidence |
| Severity | MEDIUM |
| Fake confidence | 0.85 |
| Fake human review | false |
| Fake has citations | true |
| Real confidence | 0.70 |
| Real human review | false |
| Real has citations | true |
| Real API error | false |

**What this case demonstrates**: Insufficient evidence cases are handled by the pipeline. The `evidence_insufficient` risk flag is set, but this does not automatically trigger human review (unlike privacy or legal risk). The draft is still citation-grounded. The system produces a draft even with limited evidence — the safety guard is in the human review rules, not in blocking draft generation.

---

## Cross-Case Patterns

| Pattern | Cases | Observation |
|---------|-------|------------|
| Human review on high-risk | p12_011, p12_012, p12_013, p12_014, p12_015, p12_016, p12_017, p12_018 | 8/25 cases (32%) — all privacy, legal, account security, compensation |
| No human review on routine | p12_001–p12_010, p12_019–p12_025 | 17/25 cases (68%) — product consulting, refund, logistics, complaint, technical, policy conflict |
| Identical human review triggers | all 25 cases | Both providers produced the same human review pattern — risk rule is provider-agnostic |
| Citation presence | all 25 cases | Both providers produced citations in all cases — prompt constraint is effective |
| API errors | 0 | DeepSeek API responded successfully to all 25 requests |

**Boundary**: These case studies use synthetic fixtures. Real customer service scenarios may differ significantly.
