# ticket-intake Specification

## Purpose
TBD - created by archiving change add-ticket-intake-risk-triage. Update Purpose after archive.
## Requirements
### Requirement: Raw ticket intake normalization
The system SHALL accept raw Chinese ticket text as input and produce a NormalizedTicket with cleaned text, detected language, and extracted entities.

#### Scenario: Normalize refund request ticket
- **WHEN** raw Chinese text "我申请退款，订单号123456" is submitted
- **THEN** NormalizedTicket.text contains cleaned text, language is "zh", and order_numbers contains "123456"

#### Scenario: Normalize ticket with multiple entities
- **WHEN** raw Chinese text with product name, order number, and amount is submitted
- **THEN** NormalizedTicket extracts product_name, order_numbers, and amount if present

#### Scenario: Normalize ticket with no extractable entities
- **WHEN** raw Chinese text with no identifiable entities is submitted
- **THEN** NormalizedTicket entities are empty but text is cleaned

### Requirement: Text cleaning and normalization
The system SHALL remove excessive whitespace, normalize punctuation, and strip control characters from raw ticket text.

#### Scenario: Clean excessive whitespace
- **WHEN** raw text contains multiple consecutive spaces or newlines
- **THEN** output text has normalized single spaces and single newlines

#### Scenario: Normalize Chinese punctuation
- **WHEN** raw text contains full-width punctuation (，。！？)
- **THEN** output text has normalized punctuation representation

