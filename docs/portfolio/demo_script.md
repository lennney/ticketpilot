# TicketPilot Demo Script

## Prerequisites

Before running the demo, ensure:
- Docker is running and PostgreSQL + pgvector container is up: `docker compose up -d`
- Python virtual environment is activated: `uv sync`
- Quality gate passes: `bash scripts/run_quality_gate.sh`
- Streamlit is installed (included in pyproject.toml dependencies)

## How to Start the Review Console

```bash
# From the project root:
streamlit run src/ticketpilot/review/console.py
```

This launches the Streamlit human review console in your browser (default: http://localhost:8501).

## Sample RawTicket JSON Inputs

### GC1: Standard Refund Request
```json
{
  "original_text": "我要退款，订单号是 12345",
  "submitted_at": "2026-05-02T10:00:00",
  "customer_id": "C001"
}
```

### GC2: Refund with Compensation Demand (High Risk)
```json
{
  "original_text": "我要退款，你们发的货是坏的，我要赔偿！订单号 12345",
  "submitted_at": "2026-05-02T10:00:00",
  "customer_id": "C002"
}
```

### GC6: Legal Threat (Highest Risk)
```json
{
  "original_text": "你们的行为是欺诈，我要找律师起诉你们，赔偿我的损失！",
  "submitted_at": "2026-05-02T10:00:00",
  "customer_id": "C006"
}
```

### GC8: Vague/Lazy Ticket (Insufficient Evidence)
```json
{
  "original_text": "帮忙看看",
  "submitted_at": "2026-05-02T10:00:00",
  "customer_id": "C008"
}
```

## Demo Flow Step-by-Step

### Step 1: Start Console
1. Open terminal and navigate to project root
2. Run: `streamlit run src/ticketpilot/review/console.py`
3. Browser opens to Streamlit console
4. **Point out**: The console title says "TicketPilot Review Console" and the disclaimer "审核控制台 — 不自动发送回复" (Does Not Auto-Send Replies)

### Step 2: Process a Simple Refund Ticket
1. Paste GC1 JSON into the RawTicket input text area
2. Click "Process Ticket"
3. **Point out**:
   - Ticket info section: ticket_id, customer_id, raw text
   - Intent: REFUND with confidence score
   - Risk assessment: no flags triggered (neutral/green)
   - Evidence candidates: FAQ/policy documents retrieved from knowledge base
   - Draft reply: template-based response with `[N]` citation markers
   - Review trigger reasons: empty (no manual review needed)

### Step 3: Process a High-Risk Ticket
1. Paste GC2 JSON (compensation demand)
2. Click "Process Ticket"
3. **Point out**:
   - Risk assessment now shows COMPENSATION_RISK flag (red/highlighted)
   - Severity is MEDIUM or HIGH
   - `must_human_review` is True
   - Draft reply confidence is capped at 0.5
   - Review trigger reasons section shows "high_risk"

### Step 4: Demonstrate Review Actions
1. With GC2 result displayed, demonstrate each action:
   - **APPROVE**: Click "Approve". Observe "Review recorded" notification.
   - **EDIT**: Edit the draft text, click "Save Edited". Observe confirmation.
   - **ESCALATE**: Enter escalation reason, click "Escalate".
   - **REJECT**: Enter rejection reason, click "Reject".
2. **Point out**: No action sends the reply anywhere. The review history shows each decision.

### Step 5: Review History
1. Click "Load Reviews" to show all recorded decisions
2. **Point out**: Each record is complete -- ticket_id, action, risk_flags, evidence count, etc.
3. The reviews are stored in `data/reviews.jsonl` (append-only, never modified or deleted)

### Step 6: Process Insufficient Evidence Ticket
1. Paste GC8 JSON ("help look")
2. **Point out**:
   - Intent: OTHER (low confidence)
   - Risk flags include INSUFFICIENT_EVIDENCE and LOW_CONFIDENCE
   - `must_human_review` is True
   - Draft reply: safe fallback message with no policy promises, confidence=0.0, no citations
   - Review trigger reasons shows "no_evidence"

## Expected Outputs at a High Level

### Successful Processing
- TicketOutput fields populated: normalized_ticket, classification, risk_assessment, evidence_candidates, retrieval_trace
- DraftReply generated with citations (if evidence available)
- Review decisions persisted to JSONL

### Error Scenarios
- Invalid JSON input: error message displayed in Streamlit, no crash
- Database unavailable: pipeline still runs, evidence will be empty, INSUFFICIENT_EVIDENCE flag set
- Streamlit session state issues: refresh the page

## Fallback / High-Risk Demo Scenario

### If Database is Unavailable
- The pipeline will still process tickets through intake, classification, and risk assessment
- Retrieval stage will produce empty evidence (no DB connection)
- INSUFFICIENT_EVIDENCE flag will be added automatically
- Draft generation will produce a safe fallback message with no citations
- This demonstrates the graceful degradation design at every layer

### To Test Without Database
```bash
docker compose down
streamlit run src/ticketpilot/review/console.py
# Process any ticket -- observe pipeline still runs end-to-end
```

### If Streamlit Fails to Start
- Ensure all dependencies are installed: `uv sync`
- Check Python version: `python --version` (must be 3.10+)
- Try running with verbose output: `streamlit run src/ticketpilot/review/console.py --logger.level=debug`

## What NOT to Claim During Demo

| Do NOT Say | Instead Say |
|-----------|-------------|
| "The system uses AI to understand tickets" | "The system uses deterministic rules for classification and risk assessment" |
| "The retrieval finds relevant knowledge" | "The retrieval pipeline mechanics work; default embeddings are fake with no semantic meaning; real embeddings available opt-in" |
| "The draft replies are generated by AI" | "The draft replies use template-based generation / deterministic FakeLLM with evidence citations" |
| "This is production-ready" | "This is an MVP focused on proving the pipeline architecture and iteration methodology" |
| "The system can send replies automatically" | "The system requires human review; no auto-send capability exists" |
| "The embeddings capture semantic meaning" | "Default embeddings are fake -- they verify pipeline mechanics only. Real embeddings (DashScope) available opt-in" |
| "The knowledge base contains real data" | "The knowledge base contains 106 synthetic seed documents for demo and testing" |
| "The evaluation shows good retrieval quality" | "Unit tests (~856) and integration tests (119) verify correctness. Doc-ID Recall@10=91.9% under granular evaluation" |
| "Real LLM generates the replies" | "A deterministic FakeLLMProvider generates evidence-constrained drafts, no real LLM involved by default" |
