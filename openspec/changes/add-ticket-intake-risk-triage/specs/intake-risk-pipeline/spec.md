## ADDED Requirements

### Requirement: End-to-end intake-risk pipeline
The system SHALL process a raw Chinese ticket through: intake -> classification -> risk assessment -> TicketOutput.

#### Scenario: Full pipeline processing
- **WHEN** RawTicket is passed to intake_risk_pipeline()
- **THEN** returns TicketOutput with all sub-fields populated

#### Scenario: Pipeline with minimal input
- **WHEN** RawTicket with only original_text is passed
- **THEN** returns TicketOutput with empty entities and "other" classification

#### Scenario: Pipeline preserves original input
- **WHEN** RawTicket is processed
- **THEN** TicketOutput.raw_ticket.original_text equals input original_text

### Requirement: Pipeline error handling
The system SHALL handle processing errors gracefully and return partial results with error information.

#### Scenario: Pipeline handles classification failure
- **WHEN** classification raises an exception
- **THEN** TicketOutput is returned with classification.intent="OTHER" and risk flag "low_confidence"

### Requirement: Deterministic output
The system SHALL produce deterministic output for same input (no random elements in first vertical slice).

#### Scenario: Same input produces same output
- **WHEN** same RawTicket is processed twice
- **THEN** both TicketOutput objects are identical

### Requirement: Pipeline integration with Pydantic
The system SHALL use Pydantic models throughout and validate all intermediate and final outputs.

#### Scenario: Schema validation at each stage
- **WHEN** intake produces NormalizedTicket
- **THEN** it passes Pydantic validation before passing to next stage
