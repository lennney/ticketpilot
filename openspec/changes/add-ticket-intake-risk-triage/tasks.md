## 1. Project structure and schema definitions

- [ ] 1.1 Create `src/ticketpilot/__init__.py` with package exports
- [ ] 1.2 Create `src/ticketpilot/schema/__init__.py`
- [ ] 1.3 Create `src/ticketpilot/schema/ticket.py` with RawTicket, NormalizedTicket, IntentClass enum, ClassificationResult, RiskFlag enum, RiskAssessment, TicketOutput Pydantic models
- [ ] 1.4 Verify schema validation with basic instantiation test

## 2. Ticket intake module

- [ ] 2.1 Create `src/ticketpilot/intake/__init__.py`
- [ ] 2.2 Create `src/ticketpilot/intake/normalizer.py` with text cleaning and normalization functions
- [ ] 2.3 Create `src/ticketpilot/intake/entity_extractor.py` with regex patterns for order numbers, product info, amounts
- [ ] 2.4 Create `src/ticketpilot/intake/pipeline.py` combining normalizer and entity extractor into intake() function
- [ ] 2.5 Write unit tests for intake module

## 3. Intent classification module

- [ ] 3.1 Create `src/ticketpilot/classification/__init__.py`
- [ ] 3.2 Create `src/ticketpilot/classification/rules.py` with keyword dictionaries for 8 intent classes in Chinese
- [ ] 3.3 Create `src/ticketpilot/classification/classifier.py` with rule-based classify() function returning ClassificationResult
- [ ] 3.4 Write unit tests for classification module covering all 8 classes

## 4. Risk assessment module

- [ ] 4.1 Create `src/ticketpilot/risk/__init__.py`
- [ ] 4.2 Create `src/ticketpilot/risk/rules.py` with keyword patterns for 8 risk flags
- [ ] 4.3 Create `src/ticketpilot/risk/assessor.py` with assess() function returning RiskAssessment
- [ ] 4.4 Implement severity calculation based on flag count
- [ ] 4.5 Write unit tests for risk module covering all 8 flags

## 5. Intake-risk pipeline integration

- [ ] 5.1 Create `src/ticketpilot/pipeline.py` combining intake -> classification -> risk -> TicketOutput
- [ ] 5.2 Implement error handling with graceful degradation
- [ ] 5.3 Write integration smoke test for full pipeline

## 6. Smoke tests

- [ ] 6.1 Create `tests/unit/test_intake_risk_triage.py`
- [ ] 6.2 Test full pipeline with sample Chinese tickets
- [ ] 6.3 Verify all 8 intent classes are producible
- [ ] 6.4 Verify all 8 risk flags can be triggered
- [ ] 6.5 Verify deterministic output (same input = same output)

## 7. Documentation and quality gate

- [ ] 7.1 Update `docs/changelog.md` with vertical slice implementation entry
- [ ] 7.2 Run quality gate: `bash scripts/run_quality_gate.sh`
- [ ] 7.3 Verify `openspec validate --all` passes

## 8. Acceptance criteria verification

- [ ] 8.1 Verify raw Chinese ticket input works
- [ ] 8.2 Verify normalized ticket output has cleaned text and entities
- [ ] 8.3 Verify 8-class intent classification with deterministic rules
- [ ] 8.4 Verify 8-flag risk assessment with severity calculation
- [ ] 8.5 Verify structured JSON output via TicketOutput schema
