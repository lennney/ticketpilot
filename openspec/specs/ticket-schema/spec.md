# ticket-schema Specification

## Purpose
TBD - created by archiving change add-ticket-intake-risk-triage. Update Purpose after archive.
## Requirements
### Requirement: RawTicket schema
The system SHALL define RawTicket with fields: original_text (str), submitted_at (datetime), customer_id (str, optional).

#### Scenario: RawTicket validation
- **WHEN** RawTicket is created with valid fields
- **THEN** it passes Pydantic validation

#### Scenario: RawTicket missing optional field
- **WHEN** RawTicket is created without customer_id
- **THEN** customer_id defaults to None

### Requirement: NormalizedTicket schema
The system SHALL define NormalizedTicket with fields: text (str), language (str), order_numbers (list[str]), product_info (str, optional), amount (float, optional), cleaned_at (datetime).

#### Scenario: NormalizedTicket validation
- **WHEN** NormalizedTicket is created with valid fields
- **THEN** it passes Pydantic validation

### Requirement: IntentClass enum
The system SHALL define IntentClass as enum with 8 values: REFUND, RETURN_EXCHANGE, ACCOUNT_ISSUE, TECHNICAL_ISSUE, PRODUCT_CONSULTING, LOGISTICS, COMPLAINT, OTHER.

#### Scenario: IntentClass enum values
- **WHEN** IntentClass enum is accessed
- **THEN** all 8 values are available

### Requirement: ClassificationResult schema
The system SHALL define ClassificationResult with fields: intent (IntentClass), confidence (float), classified_at (datetime).

#### Scenario: ClassificationResult validation
- **WHEN** ClassificationResult is created with valid fields
- **THEN** it passes Pydantic validation

### Requirement: RiskFlag enum
The system SHALL define RiskFlag as enum with 8 values: COMPLAINT_RISK, COMPENSATION_RISK, LEGAL_RISK, PRIVACY_RISK, ACCOUNT_SECURITY_RISK, POLICY_CONFLICT, INSUFFICIENT_EVIDENCE, LOW_CONFIDENCE.

#### Scenario: RiskFlag enum values
- **WHEN** RiskFlag enum is accessed
- **THEN** all 8 values are available

### Requirement: RiskAssessment schema
The system SHALL define RiskAssessment with fields: flags (set[RiskFlag]), severity (str: "low"|"medium"|"high"), assessed_at (datetime).

#### Scenario: RiskAssessment validation
- **WHEN** RiskAssessment is created with valid fields
- **THEN** it passes Pydantic validation

### Requirement: TicketOutput schema
The system SHALL define TicketOutput combining: ticket_id (str), raw_ticket (RawTicket), normalized_ticket (NormalizedTicket), classification (ClassificationResult), risk_assessment (RiskAssessment), output_at (datetime).

#### Scenario: TicketOutput validation
- **WHEN** TicketOutput is created with all sub-schemas populated
- **THEN** it passes Pydantic validation and serializes to JSON

#### Scenario: TicketOutput JSON serialization
- **WHEN** TicketOutput is serialized to JSON
- **THEN** output contains all required fields and nested structures

