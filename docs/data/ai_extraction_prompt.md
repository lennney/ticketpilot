# AI-assisted Field Extraction Prompt

## Purpose

This prompt is used to convert public or open customer-service source material (dialogue summaries, ticket excerpts, policy page summaries) into a structured **adaptation candidate** for TicketPilot.

The output is a **candidate only** — it must be reviewed by human annotators before becoming a final evaluation ticket or golden expectation.

## Input Format

```
source_name: <name of the source dataset or document>
source_type: <dialogue | ticket | policy_page | general_dialogue>
source_usage_type: <scenario_reference | wording_reference | schema_reference | policy_reference>
source_text_or_summary: <short summary or excerpt from the source material, not the full raw record>
```

## Output Format

JSON only. No explanatory text.

## Allowed Values

### issue_type (choose one)
- `refund`
- `return_exchange`
- `account_issue`
- `technical_issue`
- `product_consulting`
- `logistics`
- `complaint`
- `other`

### risk_flags (zero or more)
- `complaint_risk`
- `compensation_risk`
- `legal_risk`
- `privacy_risk`
- `account_security_risk`
- `policy_conflict`
- `insufficient_evidence`
- `low_confidence`

### evidence_doc_types (zero or more)
- `FAQ`
- `Policy`
- `Case`

## Rules

1. **AI output is candidate only.** Do not treat the output as a final golden expectation. Human review is required before any candidate becomes an evaluation ticket.

2. **Do not include real personal data.** No real names, phone numbers, ID numbers, or addresses. Use placeholders (e.g., "订单号 12345").

3. **Do not copy raw external dataset records directly.** The `adapted_ticket_text` must be a synthetic single-turn Chinese support ticket rewritten from the source, not a verbatim copy.

4. **`expected_no_auto_send` is not decided by AI.** Phase 7 architecture fixes it as `true` for all tickets.

5. **If source information is insufficient**, fill `missing_information` with what is needed and set `rewrite_needed: true`.

6. **`human_review_status`** must be `"pending"`.

7. **`ready_for_final_eval`** must be `false`.

## Output JSON Schema

```json
{
  "candidate_id": "string — unique ID for this candidate",
  "source_id": "string — reference to source registry entry",
  "source_name": "string — dataset or source name",
  "source_usage_type": "string — scenario_reference | wording_reference | schema_reference | policy_reference",
  "raw_issue_summary": "string — short summary of the source issue, not the full raw text",
  "customer_goal": "string — what the customer wants to achieve",
  "product_or_service_context": "string — ecommerce, account, payment, logistics, invoice, etc.",
  "issue_scenario": "string — specific scenario description",
  "emotion_or_escalation_signal": "string — complaint, legal threat, compensation demand, privacy concern, etc.",
  "possible_issue_type": "string — one of the 8 allowed issue types",
  "possible_risk_flags": ["string — zero or more allowed risk flags"],
  "possible_severity": "string — LOW | MEDIUM | HIGH",
  "possible_must_human_review": "boolean — true if any risk flag is present or evidence is insufficient",
  "possible_evidence_doc_types": ["string — zero or more of FAQ, Policy, Case"],
  "missing_information": ["string — list of information needed for a safe response"],
  "rewrite_needed": "boolean — true if source needs manual rewriting",
  "adapted_ticket_text": "string — synthetic single-turn Chinese support ticket",
  "scenario_group": "string — refund_complaint | privacy_account | invoice_payment | normal_case",
  "human_review_status": "string — must be \"pending\"",
  "human_review_notes": "string — empty or notes for the reviewer",
  "ready_for_final_eval": "boolean — must be false"
}
```

## Example

### Input
```
source_name: CSDS
source_type: dialogue
source_usage_type: wording_reference
source_text_or_summary: 用户投诉退款迟迟不到账，并提到要投诉平台。
```

### Output
```json
{
  "candidate_id": "cand_refund_001",
  "source_id": "src_csds_001",
  "source_name": "CSDS",
  "source_usage_type": "wording_reference",
  "raw_issue_summary": "Customer complains refund not received and threatens to complain about the platform.",
  "customer_goal": "Follow up on refund status; wants platform to take action.",
  "product_or_service_context": "ecommerce_refund",
  "issue_scenario": "Refund delay followed by complaint escalation",
  "emotion_or_escalation_signal": "Complaint threat, frustration",
  "possible_issue_type": "refund",
  "possible_risk_flags": ["complaint_risk"],
  "possible_severity": "MEDIUM",
  "possible_must_human_review": true,
  "possible_evidence_doc_types": ["Policy", "Case"],
  "missing_information": ["order_id", "refund_request_time", "refund_amount"],
  "rewrite_needed": true,
  "adapted_ticket_text": "我申请退款已经三天了还没到账，订单号是 12345。你们再不处理我就投诉。",
  "scenario_group": "refund_complaint",
  "human_review_status": "pending",
  "human_review_notes": "",
  "ready_for_final_eval": false
}
```
