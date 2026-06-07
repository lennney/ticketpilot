# TicketPilot Project Memory

## Latest Checkpoint (2026-06-07)

### Changes
- Legal intent classification: "律师/起诉/法院" → COMPLAINT (was OTHER)
- Multi-signal confidence: order number → 0.88, long text → 0.82, default → 0.78
- CLI pipeline mode: `--prediction-mode pipeline` for live evaluation
- Confidence tier boundary: `>=` instead of `>`

### Demo Results
- DEMO-005 "律师起诉": intent=COMPLAINT, confidence=0.88 (was OTHER, 0.50)
- Confidence distribution: 0.88×4, 0.82×5, 0.78×1 (was 0.80×9, 0.50×1)
- 3 distinct confidence values (was 2)

### Test Status
- 1644 passed, 0 failed
- Commit: `f1a5f93` on `master`

### PM Narrative
1. Legal threat classification gap → added keywords → automatic escalation
2. Confidence clustering → multi-signal scoring → better tier distribution

### Next Steps
- [ ] More test cases for legal classification
- [ ] Confidence calibration with real data
- [ ] A/B testing for confidence thresholds
- [ ] Dashboard for confidence distribution monitoring

## Architecture
- FastAPI + PostgreSQL + pgvector + BGE-small-zh
- Deterministic pipeline (no LLM in core)
- Multi-agent: RefundAgent, ComplaintAgent, LogisticsAgent, TechnicalAgent, DefaultAgent
- Confidence tiers: HIGH (≥0.78), MEDIUM (≥0.6), LOW (≥0.4), CRITICAL (<0.4)

## Key Files
- `src/ticketpilot/classification/classifier.py` - Intent classifier
- `src/ticketpilot/classification/rules.py` - Intent rules
- `src/ticketpilot/config/__init__.py` - Confidence thresholds
- `src/ticketpilot/drafting/schemas.py` - DraftReply schema
- `scripts/run_eval.py` - CLI evaluation runner
- `scripts/generate_product_evidence.py` - Demo evidence generator
