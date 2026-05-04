# AI-assisted Field Extraction and Ticket Adaptation

## Purpose

This document defines how AI can be used to assist the construction of TicketPilot's Phase 7 evidence pack.

AI is used as a **field extraction and adaptation assistant**, not as the final source of truth for evaluation labels. The final evaluation tickets are manually adapted synthetic Chinese single-turn support tickets. Golden expectations are confirmed by human annotators based on TicketPilot product rules.

## Positioning

- AI assists with field extraction, scenario identification, and candidate generation.
- AI does **not** produce final golden labels.
- AI-generated candidates must be reviewed by a human before becoming evaluation data.
- Raw public datasets are not directly copied into the repository.

## Pipeline

```
Public / open source record
        │
        ▼
AI-assisted field extraction — extract scenario, goal, risk signals,
  issue type candidates, evidence needs from source material
        │
        ▼
Adaptation candidate — structured TicketAdaptationCandidate with
  extracted fields, source reference, and rewrite suggestions
        │
        ▼
Human review — confirm or correct extracted fields, verify
  no PII, assess rewrite quality, finalize ticket text
        │
        ▼
Synthetic TicketPilot eval ticket — final single-turn Chinese
  support ticket written to tickets_eval.csv
        │
        ▼
Manually confirmed golden expectation — product-rule labels
  written to golden_expectations.csv
        │
        ▼
Evaluation pipeline — CSV-mode and pipeline-mode evaluation
  against golden expectations
```

## Source Reference Fields

Each adaptation candidate references a public or open source record. These fields document the origin and usage constraints.

| Field | Description | Example |
|---|---|---|
| `source_id` | Internal source identifier | `src_csds_001` |
| `source_name` | Dataset or source name | CSDS (Chinese Customer Service Dialogue Summarization) |
| `source_type` | Type of source data | `dialogue` / `ticket` / `policy_page` / `general_dialogue` |
| `source_url_or_registry_key` | Link to source registry entry | Reference to `docs/data/evidence_pack_sources.md` |
| `source_language` | Language of source | `zh` / `en` |
| `source_record_id` | Original record ID in the source dataset | Used for traceability; must not expose sensitive content |
| `source_usage_type` | How this source is used for adaptation | `scenario_reference` / `wording_reference` / `schema_reference` / `policy_reference` |
| `raw_data_committed` | Whether raw source data is committed to the repo | Always `false` unless license explicitly permits |
| `license_note` | License or access condition | Apache-2.0, CC-BY, research-only, etc. |

## AI Extraction Candidate Fields

AI extracts the following fields from source material. These are **candidates** requiring human review.

| Field | Description | Human review required |
|---|---|---|
| `candidate_id` | Candidate sample ID | N/A (identifier) |
| `source_id` | Reference to source record | N/A (copied from source) |
| `raw_issue_summary` | Short summary of the source issue | Yes — prevent misinterpretation |
| `customer_goal` | What the customer wants to achieve | Yes — affects issue_type |
| `product_or_service_context` | Domain context (e-commerce, account, payment, logistics, invoice, etc.) | Yes |
| `issue_scenario` | Scenario category (e.g., "refund not received then escalated to complaint") | Yes — affects scenario coverage |
| `emotion_or_escalation_signal` | Signals of urgency, complaint, legal threat, compensation demand, privacy concern | Yes — critical for risk flags |
| `possible_issue_type` | AI-suggested TicketPilot issue type (one of 8) | Suggest only — must be confirmed |
| `possible_risk_flags` | AI-suggested risk flags (zero or more of 8) | Suggest only — must be confirmed |
| `possible_evidence_doc_types` | AI-suggested evidence types (FAQ, Policy, Case) | Suggest only — must be confirmed |
| `missing_information` | Information needed before safe response | Yes |
| `rewrite_needed` | Whether this source needs manual rewriting | Yes |
| `adaptation_notes` | Notes for the human reviewer during adaptation | Yes |

## Final TicketPilot Eval Ticket Fields

After human review and adaptation, each ticket is written to `tickets_eval.csv` with these fields.

| Field | Type | Description |
|---|---|---|
| `ticket_id` | string | Stable evaluation ticket ID (e.g., `refund_001`) |
| `original_text` | string | Final synthetic single-turn Chinese support ticket |
| `submitted_at` | ISO datetime | Simulated submission timestamp |
| `customer_id` | string | Synthetic customer ID (not real) |
| `source_reference` | string | Link to source registry (e.g., `src_csds_001`) |
| `adaptation_method` | string | `manual_rewrite_from_public_reference` or `synthetic_from_policy_reference` |
| `scenario_group` | string | Scenario group: `refund_complaint` / `privacy_account` / `invoice_payment` / `normal_case` |

## Golden Expectation Fields

Each eval ticket has one golden expectation row in `golden_expectations.csv`.

| Field | Type | Required | Description |
|---|---|---|---|
| `ticket_id` | string | yes | Matches the eval ticket ID |
| `expected_issue_type` | string enum | yes | One of 8 fixed issue types |
| `expected_risk_flags` | string list | yes | Zero or more risk flags (pipe-delimited if CSV) |
| `expected_severity` | string enum | yes | LOW / MEDIUM / HIGH |
| `expected_must_human_review` | boolean | yes | Whether the pipeline must route to human review |
| `expected_relevant_doc_ids` | string list | no | Expected evidence document IDs (optional) |
| `expected_doc_types` | string list | yes | Expected evidence doc type coverage (FAQ / Policy / Case) |
| `expected_fallback_behavior` | string enum | yes | `evidence_supported_draft` / `no_evidence_fallback` / `human_review_required` / `policy_conflict_escalation` |
| `expected_no_auto_send` | boolean | yes | Always `true` for Phase 7 (architecture guarantee) |
| `unacceptable_behavior` | text | no | Behaviors the system MUST NOT exhibit for this ticket |
| `annotation_notes` | text | no | Human annotation rationale, edge case notes, scenario context |

### expected_no_auto_send annotation rule

For Phase 7, `expected_no_auto_send` is `true` for **every** evaluation ticket.

This is an architectural guarantee: TicketPilot only generates drafts and never sends final customer replies automatically. There is no send channel — no API, no message queue, no webhook. This field is not a model behavior metric.

## AI vs Human Responsibility Matrix

| Field or task | AI role | Human role |
|---|---|---|
| `raw_issue_summary` | Generate candidate summary | Review and correct |
| `customer_goal` | Extract candidate goal | Confirm or reassign |
| `issue_scenario` | Categorize scenario | Confirm or recategorize |
| `possible_issue_type` | Suggest one of 8 types | **Must confirm** — this is part of the evaluation label |
| `possible_risk_flags` | Suggest risk flags | **Must confirm** — especially high-risk flags |
| `possible_evidence_doc_types` | Suggest FAQ/Policy/Case | **Must confirm** — affects retrieval evaluation |
| `original_text` rewrite | Generate candidate rewrite | Review for naturalness, PII, and scenario fit |
| `expected_issue_type` | Suggest only | **Must confirm** — golden label cannot be AI-only |
| `expected_risk_flags` | Suggest only | **Must confirm** — golden label cannot be AI-only |
| `expected_severity` | Suggest only | **Must confirm** — follows risk rules |
| `expected_must_human_review` | Suggest only | **Must confirm** — critical routing decision |
| `expected_doc_types` | Suggest only | **Must confirm** — retrieval evaluation target |
| `expected_fallback_behavior` | Suggest only | **Must confirm** — depends on evidence availability |
| `expected_no_auto_send` | Not needed | Set by rule: always `true` |
| `unacceptable_behavior` | Suggest candidates | Review and finalize |
| `annotation_notes` | Draft notes | Review and complete |

**Summary**: AI is a data preparation assistant. Humans are the final annotators. Golden labels must not be AI-only.

## Human Review Trigger Rules

Human review is **mandatory** when the AI extraction candidate contains any of the following signals. The reviewer must confirm or correct all fields before the candidate becomes a final evaluation ticket.

| Trigger | Reason |
|---|---|
| Legal risk suggested (`legal_risk`) | False positive/negative has high cost; escalation signal must be verified |
| Privacy risk suggested (`privacy_risk`) | PII handling and privacy scenario accuracy must be confirmed |
| Account security risk suggested (`account_security_risk`) | Security incident scenarios must be realistic and properly labeled |
| Compensation demand | Compensation-related tickets directly affect severity and human review routing |
| Refund promise in draft | System must not promise refunds without policy evidence; golden label must reflect this constraint |
| Policy conflict possible | Customer request that may conflict with documented policy; fallback or escalation may be needed |
| Insufficient evidence | No-evidence fallback expectations must be explicitly annotated |
| Low confidence | Ambiguous intent or risk classification affects evaluation interpretation |
| Ambiguous issue type | When AI suggests multiple possible issue types or confidence is split |

## Prohibited Practices

The following practices are **not allowed** in Phase 7 evidence pack construction:

1. **No raw external data commits** — Do not commit raw external datasets unless the license explicitly allows redistribution. Only adapted synthetic tickets and their source references belong in the repo.

2. **No AI-only golden labels** — Do not treat AI-generated labels as final golden expectations. Every golden label must be reviewed and confirmed by a human.

3. **No real personal data** — Do not include real names, phone numbers, ID numbers, addresses, or any personally identifiable information.

4. **No real enterprise validation claims** — The evidence pack does not validate against real enterprise data or production performance.

5. **No production readiness claims** — TicketPilot is a local demo / portfolio project. The evidence pack does not make it production-ready.

6. **No fake embedding as semantic proof** — Fake embedding (384-dim deterministic hash) cosine similarity has no semantic meaning. Do not cite Phase 7 evaluation numbers as evidence of real semantic retrieval quality.

7. **No auto-send** — TicketPilot only generates drafts. No send channel exists. No evaluation metric should imply otherwise.

## Example

### Source reference
CSDS dialogue excerpt (summarized): "用户投诉退款迟迟不到账，并提到要投诉平台。"

### AI extraction candidate
```
candidate_id: cand_refund_001
source_id: src_csds_001
raw_issue_summary: Customer complains refund not received and threatens to complain about the platform.
customer_goal: Follow up on refund status; wants platform to take action.
product_or_service_context: E-commerce refund
issue_scenario: Refund delay → complaint escalation
emotion_or_escalation_signal: Complaint threat, frustration
possible_issue_type: refund (primary) / complaint (secondary)
possible_risk_flags: [complaint_risk]
possible_evidence_doc_types: [Policy, Case]
missing_information: order_id, refund_request_time, refund amount
rewrite_needed: yes
adaptation_notes: Add synthetic order number; keep complaint tone realistic but not overly aggressive.
```

### Final adapted ticket
```
我申请退款已经三天了还没到账，订单号是 12345。你们再不处理我就投诉。
```

### Golden expectation
```
ticket_id: refund_complaint_001
expected_issue_type: refund
expected_risk_flags: [complaint_risk]
expected_severity: MEDIUM
expected_must_human_review: true
expected_doc_types: [Policy, Case]
expected_fallback_behavior: evidence_supported_draft
expected_no_auto_send: true
unacceptable_behavior: Must not promise refund approval without policy check; must not ignore complaint_risk flag.
annotation_notes: Mixed refund+complaint. Primary intent is refund follow-up, but complaint language requires human review.
```
