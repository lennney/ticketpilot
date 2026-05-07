# TicketPilot Demo Guide

> Local demo guide — three demo tracks covering the full ticket processing workflow.
>
> **This is a local portfolio demo, not a production system.**

## Prerequisites

Complete the [Quick Start](../../README.md#6-快速开始) steps first:

```bash
# 1. Install dependencies
uv sync

# 2. Start PostgreSQL (requires Docker)
docker compose up -d

# 3. Run database migrations (via Docker init)
# Note: alembic.ini is not configured; migrations run automatically on first container start

# 4. Import seed knowledge
uv run python scripts/ingest_knowledge.py

# 5. Verify environment
./scripts/run_quality_gate.sh
```

---

## Demo Track A: Normal Post-Sale Tickets

**Goal:** Show a typical refund/return ticket through the full pipeline.

### Step 1: Start the Human Review Console

```bash
uv run streamlit run src/ticketpilot/review/console.py
```

Open http://localhost:8501.

### Step 2: Submit a Refund Ticket

```python
from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.schema.ticket import RawTicket
from datetime import datetime

ticket = RawTicket(
    original_text="我要退款，订单号：123456，收到的商品有质量问题。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_001"
)
result = intake_risk_pipeline(ticket)

print("=== Intent Classification ===")
print(f"Type: {result.classification.intent.value}")
print(f"Confidence: {result.classification.confidence:.2f}")

print("\n=== Risk Assessment ===")
print(f"Severity: {result.risk_assessment.severity.value}")
print(f"Risk flags: {[f.value for f in result.risk_assessment.flags]}")
print(f"Human review required: {result.risk_assessment.must_human_review}")
```

**Key points to show:**
- `intent` = `refund` (8-class classification)
- `severity` = `low` (severity calculation logic)
- `evidence_candidates` from FAQ/Policy/Case document types
- Approve action in the Streamlit console

### Step 3: Try a Return/Exchange Ticket

```python
ticket = RawTicket(
    original_text="我想退货换货，订单号：654321，尺码不合适。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_002"
)
result = intake_risk_pipeline(ticket)
```

**Key points to show:**
- Different `intent` from refund (`return_exchange` vs `refund`)
- No risk flags, `severity` = `low`

---

## Demo Track B: High-Risk Tickets

**Goal:** Show how the system identifies high-risk tickets and forces human review.

### High-Risk Complaint + Compensation

```python
ticket = RawTicket(
    original_text="客服态度太差了，我要投诉！要求3倍赔偿，不然我就找律师起诉你们。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_003"
)
result = intake_risk_pipeline(ticket)

print("=== Risk Assessment ===")
print(f"Severity: {result.risk_assessment.severity.value}")
print(f"Risk flags: {[f.value for f in result.risk_assessment.flags]}")
print(f"Human review required: {result.risk_assessment.must_human_review}")
```

**Key points to show:**
- Multiple risk flags: `complaint_risk` + `compensation_risk` + `legal_risk`
- `severity` upgrades to `high` due to multiple flags
- `must_human_review = true`
- Escalate or Reject action in console

### Privacy / Account Security

```python
ticket = RawTicket(
    original_text="我的账号被冻结了，个人信息可能泄露了，手机号被他人使用。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_004"
)
result = intake_risk_pipeline(ticket)
```

**Key points to show:**
- `intent` = `account_issue`
- Risk flags = `account_security_risk` + `privacy_risk`
- Triggers `must_human_review`

### Weak Evidence / Short Input

```python
ticket = RawTicket(
    original_text="退款。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_005"
)
result = intake_risk_pipeline(ticket)
```

**Key points to show:**
- Even short input gets classified correctly
- May trigger `insufficient_evidence` flag
- Shows fallback behavior — system doesn't fabricate information

---

## Demo Track C: Evaluation Reports

**Goal:** Show the offline evaluation pipeline.

### CSV Prediction Mode

```bash
uv run python scripts/run_eval.py \
  --tickets data/eval/tickets_eval.csv \
  --golden data/eval/golden_expectations.csv \
  --predictions data/eval/sample_predictions.csv \
  --out-json reports/eval/evaluation_report.json \
  --out-md reports/eval/evaluation_report.md
```

View the report:
```bash
cat reports/eval/evaluation_report.md
```

**Key points to show:**
- 7 evaluation metrics (intent_accuracy, severity_accuracy, risk flag F1, evidence_doc_type_recall, fallback_correctness, must_human_review_accuracy, no_auto_send_compliance)
- Evaluation based on seed data, not real-world data
- Fake embedding limitations stated

### Pipeline Prediction Mode

```bash
uv run python scripts/run_eval.py \
  --tickets data/eval/tickets_eval.csv \
  --golden data/eval/golden_expectations.csv \
  --prediction-mode pipeline \
  --out-json reports/eval/current_pipeline_report.json \
  --out-md reports/eval/current_pipeline_report.md
```

**Key points to show:**
- Pipeline mode runs the full pipeline to generate predictions
- Limitations clearly stated: seed data, fake embedding, non-real-world performance

---

## Quick Reference Table

| # | Scenario | Intent | Severity | Risk Flags | Human Review |
|---|----------|--------|----------|------------|--------------|
| 1 | Refund - quality issue | `refund` | `low` | (none) | No |
| 2 | Return/exchange - size | `return_exchange` | `low` | (none) | No |
| 3 | Logistics query | `logistics` | `low` | (none) | No |
| 4 | Account frozen | `account_issue` | `medium` | `account_security_risk` | Maybe |
| 5 | Complaint + compensation + legal | `complaint` | `high` | 3 flags | **Yes** |
| 6 | Privacy leak | `account_issue` | `high` | `privacy_risk` | **Yes** |
| 7 | Just "refund" | `refund` | `low` | `insufficient_evidence` | Maybe |

---

## What NOT to Claim

- NOT a production-grade customer service system
- NOT real semantic retrieval quality (fake embeddings)
- NOT real enterprise data coverage (seed data only)
- NOT LLM capability (template-based generation)
- NOT auto-send (no-auto-send is architectural)

---

## Troubleshooting

### Database connection fails

```bash
docker compose ps
docker compose logs postgres
```

### Streamlit won't start

```bash
uv run streamlit run src/ticketpilot/review/console.py --logger.level=debug
```

### All evaluation reports go to `reports/eval/`

---

*TicketPilot — Local demo / portfolio project. See [README.md](../../README.md).*