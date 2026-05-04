# Golden Expectation Annotation Guide

## Purpose

Golden expectations define the expected behavior of TicketPilot for each evaluation ticket. They are **product-rule labels**, not model-generated labels. Each label reflects what the system SHOULD do given the ticket content and the current pipeline rules — not what an LLM or human agent would say.

## Required fields

Each evaluation ticket MUST have exactly one golden expectation row.

| Field | Type | Required | Description |
|---|---|---|---|
| `ticket_id` | string | yes | Matches the eval ticket ID |
| `expected_issue_type` | string enum | yes | One of 8 fixed issue types |
| `expected_risk_flags` | string list | yes | Zero or more risk flags (pipe-delimited if CSV) |
| `expected_severity` | string enum | yes | LOW / MEDIUM / HIGH |
| `expected_must_human_review` | boolean | yes | Whether the pipeline must route to human review |
| `expected_relevant_doc_ids` | string list | no | Expected evidence document IDs (optional) |
| `expected_doc_types` | string list | yes | Expected evidence doc type coverage (FAQ / Policy / Case) |
| `expected_fallback_behavior` | string enum | yes | Expected fallback mode |
| `expected_no_auto_send` | boolean | yes | MUST be true for all tickets (architecture guarantee) |
| `unacceptable_behavior` | text | no | What the system MUST NOT do for this ticket |
| `annotation_notes` | text | no | Rationale, edge case notes, or scenario context |

## Field definitions

### expected_issue_type

Must be one of:
- `refund` — 退款
- `return_exchange` — 退换货
- `account_issue` — 账号问题
- `technical_issue` — 技术问题
- `product_consulting` — 产品咨询
- `logistics` — 物流
- `complaint` — 投诉
- `other` — 其他

Select the single best-fit type based on the customer's primary request.

### expected_risk_flags

Zero or more of the following, reflecting risk signals in the ticket text:

- `complaint_risk` — Customer expresses dissatisfaction or threatens complaint escalation.
- `compensation_risk` — Customer demands monetary or non-monetary compensation.
- `legal_risk` — Customer mentions lawyer, legal action, lawsuit, or regulatory complaint.
- `privacy_risk` — Customer reports personal information leakage, unauthorized data use, or privacy violation.
- `account_security_risk` — Customer reports account theft, unauthorized login, or account abnormality.
- `policy_conflict` — Customer's request conflicts with existing policy (e.g., refund past deadline).
- `insufficient_evidence` — Customer provides insufficient detail for evidence-based resolution.
- `low_confidence` — Intent or risk classification confidence is below threshold.

If no risk is detected, use an empty list.

### expected_severity

| Value | When to apply |
|---|---|
| `LOW` | Routine request, no risk flags, standard resolution path |
| `MEDIUM` | One or more moderate risk flags present; requires attention but not immediate escalation |
| `HIGH` | Legal risk, explicit privacy leakage, compensation demands, or combination of multiple substantive risks |

Rules:
- `legal_risk` forces HIGH severity.
- Privacy leakage and account security incidents SHOULD usually be HIGH.
- Multiple substantive risks increase severity (e.g., complaint + compensation = at least MEDIUM).
- `insufficient_evidence` and `low_confidence` trigger review but do NOT by themselves raise severity above LOW.

### expected_must_human_review

Boolean. MUST be `true` if ANY of the following apply:
- Any risk flag is present (even `insufficient_evidence` or `low_confidence`).
- Evidence is insufficient for evidence-grounded drafting.
- Legal, privacy, or account-security risk exists.
- The ticket asks for unsupported compensation, refund exception, or policy override.
- The draft would require fallback (no_evidence or generation_error).

MUST be `false` only when ALL of the following are true:
- No risk flags detected.
- Evidence is available and sufficient.
- The request is routine and policy-supported.

### expected_doc_types

A set of expected evidence document types that SHOULD be retrieved for this ticket:

- `FAQ` — Frequently asked questions / standard answers.
- `Policy` — Policy documents (return policy, privacy policy, billing policy).
- `Case` — Historical case resolutions / precedents.

This field evaluates whether retrieval selected the **right type** of evidence, not whether the reply sounds fluent.

### expected_fallback_behavior

| Value | When to use |
|---|---|
| `evidence_supported_draft` | Normal case: evidence was retrieved and draft cites it |
| `no_evidence_fallback` | No relevant evidence found; draft uses fallback template |
| `human_review_required` | Risk flags triggered but evidence may be partial; system flags for review |
| `policy_conflict_escalation` | Customer request explicitly conflicts with policy; escalation required |

### expected_no_auto_send

For TicketPilot Phase 7, this MUST be `true` for **every** ticket, because:
- The system only produces **drafts**.
- No send channel exists (no API, no message queue, no webhook).
- The architecture-level constraint is: all output is review-suggestions, not sent replies.

This field is **not** a model behavior metric. It is an architectural compliance check.

### unacceptable_behavior

Examples of behaviors that MUST NOT occur:
- Promises refund without policy evidence.
- Promises compensation without human review.
- Ignores legal threat (e.g., "律师函" mentioned but treated as routine).
- Ignores privacy leakage (e.g., "手机号被泄露" but no privacy risk flag raised).
- Sends final reply automatically (violates no-auto-send architecture).
- Fabricates policy (cites policy that does not exist in the knowledge base).
- Cites missing evidence (citation references a document not in retrieved set).

### annotation_notes

Free-text field for rationale, edge cases, and scenario context. Examples:
- "Mixed refund+complaint intent; primary intent is refund."
- "Customer mentions lawyer; legal_risk should fire regardless of refund ask."
- "Short text with minimal context; expected fallback is no_evidence."
- "Known edge case: policy_conflict because refund window has expired."

## Annotation principles

1. **Risk recall is more important than smooth reply wording.** Flagging a genuine risk outweighs the cost of a false-positive flag in evaluation. The system should err toward flagging ambiguous risk signals.

2. **Evidence support is more important than natural generation.** The evaluation measures whether the right evidence types were retrieved, not whether the draft reads naturally.

3. **High-risk tickets SHOULD prefer escalation over overconfident automation.** If there is doubt about whether a ticket requires human review, the golden expectation SHOULD lean toward `must_human_review=true`.

4. **Unsupported customer demands SHOULD trigger review or fallback.** If the customer asks for something the policy does not support, the system must not generate a compliant-sounding draft. Fallback or human review is the correct response.

5. **The golden label reflects product policy, not what sounds convenient.** Labels should be consistent with the documented risk rules and drafting behavior, not with what a human agent might ideally do.
