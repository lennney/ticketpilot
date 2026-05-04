# add-mvp-evidence-pack — Knowledge Base Specification

## Baseline (Before Change)

- FAQ records: 12 (7 business domains)
- Policy records: 12 (7 business domains)
- Case records: 12 (7 business domains)
- Total records: 36
- Business domains covered: refund, return_exchange, account, logistics, complaint, technical, product_consulting
- Business domains missing: billing/invoice, payment_dispute, privacy/data_protection
- All content: synthetic Chinese customer service knowledge entries

## ADDED Requirements

### Requirement: Knowledge Base Expansion — FAQ
The system SHALL expand `data/knowledge/faq_seed.json` to approximately 40 synthetic FAQ records.

#### Scenario: FAQ records total ~40
- WHEN `data/knowledge/faq_seed.json` is loaded
- THEN len(records) >= 35 AND len(records) <= 50

#### Scenario: New FAQ business domains present
- WHEN FAQ records are loaded
- THEN at least 5 records have business_domain = "billing" or "invoice"
- AND at least 5 records have business_domain = "payment"
- AND at least 5 records have business_domain = "privacy" or "data_protection"

#### Scenario: All FAQ records have required fields
- WHEN each FAQ record is validated
- THEN every record has non-empty id, doc_type="FAQ", business_domain, title, content, intent_tags

### Requirement: Knowledge Base Expansion — Policy
The system SHALL expand `data/knowledge/policy_seed.json` to approximately 30 synthetic policy records.

#### Scenario: Policy records total ~30
- WHEN `data/knowledge/policy_seed.json` is loaded
- THEN len(records) >= 25 AND len(records) <= 40

#### Scenario: New policy domains present
- WHEN policy records are loaded
- THEN at least 3 records have business_domain = "billing" or "invoice"
- AND at least 3 records have business_domain = "payment"
- AND at least 3 records have business_domain = "privacy" or "data_protection"

#### Scenario: All policy records have required fields
- WHEN each policy record is validated
- THEN every record has non-empty id, doc_type="POLICY", business_domain, policy_code, title, content, effective_date

### Requirement: Knowledge Base Expansion — Case
The system SHALL expand `data/knowledge/case_seed.json` to approximately 25 synthetic case resolution records.

#### Scenario: Case records total ~25
- WHEN `data/knowledge/case_seed.json` is loaded
- THEN len(records) >= 20 AND len(records) <= 35

#### Scenario: New case business domains present
- WHEN case records are loaded
- THEN at least 3 records have business_domain = "billing" or "invoice"
- AND at least 3 records have business_domain = "payment"
- AND at least 3 records have business_domain = "privacy"

#### Scenario: All case records have required fields
- WHEN each case record is validated
- THEN every record has non-empty id, doc_type="CASE", business_domain, case_id, issue_summary, resolution, risk_level

### Requirement: Knowledge Base Total Size
The expanded knowledge base SHALL contain 80–120 total records across all three doc types.

#### Scenario: Total knowledge base size in range
- WHEN FAQ, Policy, and Case records are loaded and counted
- THEN the sum total is >= 80 AND <= 120

## MODIFIED Requirements

(None — existing knowledge schemas are unchanged. Only the data files are expanded.)

## DELETED Requirements

(None)

## Data Sources

- All knowledge entries are **synthetic**: manually crafted Chinese customer service documents.
- No real enterprise knowledge base, policy documents, or case records are used.
- Content is designed to match the expanded eval ticket domains (billing, payment, privacy).
- Fake embedding limitation remains: vector search uses deterministic hash-based 384-dim vectors.
- Semantic retrieval quality is not tested or claimed.

## Validation

- Knowledge data files load without error via existing ingestion mechanisms
- All records have valid doc_type values (FAQ/POLICY/CASE)
- No duplicate IDs within a file
- OpenSpec validate --all passes
- Quality gate passes
