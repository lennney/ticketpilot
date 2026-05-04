# add-mvp-evidence-pack — Data Sources and Methodology Specification

## Baseline (Before Change)

- No data sources documentation existed.
- No evaluation dataset methodology document existed.
- No golden expectation annotation guide existed.
- Eval tickets (10) and knowledge records (36) were created ad-hoc without a documented source attribution policy.

## ADDED Requirements

### Requirement: Data Sources Documentation
The system SHALL provide a data sources document at `docs/data/evidence_pack_sources.md` that records all external datasets and sources used as reference for the Phase 7 evidence pack.

#### Scenario: Source registry exists
- WHEN `docs/data/evidence_pack_sources.md` is read
- THEN it contains a source registry table with columns: Source, Type, Language, Original task, TicketPilot usage, Raw data committed?, License/access note, Limitations

#### Scenario: CSDS is listed with usage and limitations
- WHEN the source registry is read
- THEN CSDS (Chinese Customer Service Dialogue Summarization) is listed as a Chinese customer-service dialogue wording/scenario reference
- AND its limitation (dialogue format, not single-turn ticket format) is documented

#### Scenario: Kaggle datasets are listed
- WHEN the source registry is read
- THEN at least one Kaggle customer support ticket dataset is listed as a schema/category reference
- AND its English-language limitation is documented

#### Scenario: Chinese Chatbot Corpus is listed
- WHEN the source registry is read
- THEN Chinese Chatbot Corpus is listed as an informal Chinese expression reference
- AND its non-customer-service-specific limitation is documented

#### Scenario: Public policy pages are listed
- WHEN the source registry is read
- THEN public after-sales policy pages are listed as reference for synthetic FAQ/Policy/Case knowledge records
- AND the "no direct copy" rule is documented

#### Scenario: No raw external data committed
- WHEN the source registry is read
- THEN every entry has "Raw data committed?" = "No" or "No direct copy"

#### Scenario: Dataset adaptation rule documented
- WHEN `docs/data/evidence_pack_sources.md` is read
- THEN it documents that raw public records are not directly treated as TicketPilot evaluation tickets
- AND that each final ticket is manually rewritten into a synthetic single-turn support ticket

### Requirement: Evaluation Dataset Methodology Document
The system SHALL provide an evaluation dataset methodology document at `docs/data/evaluation_dataset_methodology.md` that describes how public reference sources become TicketPilot evaluation tickets.

#### Scenario: Construction pipeline is documented
- WHEN `docs/data/evaluation_dataset_methodology.md` is read
- THEN it documents a construction pipeline from public reference sources through to golden expectation annotation and limitations update

#### Scenario: Ticket construction rules are defined
- WHEN the methodology document is read
- THEN it defines that each final ticket MUST be single-turn, Chinese, customer-service-oriented, free of real personal data, manually adapted, and mapped to one of 8 fixed issue types

#### Scenario: Scenario coverage target documented
- WHEN the methodology document is read
- THEN it documents the Phase 7 target of approximately 100 tickets with a recommended distribution across issue types

#### Scenario: Risk coverage target documented
- WHEN the methodology document is read
- THEN it documents that the dataset MUST include all 8 risk flag types
- AND lists required high-risk example categories

#### Scenario: Three demo scenarios are defined
- WHEN the methodology document is read
- THEN it defines three strong demo scenarios: refund complaint, privacy/account issue, and invoice/payment issue
- AND each scenario documents expected pipeline behavior

### Requirement: Golden Expectation Annotation Guide
The system SHALL provide a golden expectation annotation guide at `docs/data/golden_expectation_annotation_guide.md` that defines how golden labels are assigned.

#### Scenario: Required fields are documented
- WHEN `docs/data/golden_expectation_annotation_guide.md` is read
- THEN it lists all required fields for a golden expectation entry

#### Scenario: Field definitions exist for all fields
- WHEN the annotation guide is read
- THEN every required field has a definition with allowed values and selection rules

#### Scenario: No-auto-send field is defined as architecture guarantee
- WHEN the annotation guide is read
- THEN `expected_no_auto_send` is documented as an architecture-level constraint (always true), not a model behavior metric

#### Scenario: Annotation principles are documented
- WHEN the annotation guide is read
- THEN it documents at least 5 annotation principles covering risk recall, evidence support, escalation preference, unsupported demands, and product policy alignment

### Requirement: AI-assisted Field Extraction and Adaptation Document
The system SHALL provide an AI-assisted field extraction and adaptation document at `docs/data/ai_field_extraction_adaptation.md` that defines the structured pipeline from public source through AI extraction to human-reviewed final tickets.

#### Scenario: AI positioning is documented
- WHEN `docs/data/ai_field_extraction_adaptation.md` is read
- THEN it states that AI is a field extraction and adaptation assistant, not the final source of truth for evaluation labels

#### Scenario: Full pipeline is documented
- WHEN the AI extraction document is read
- THEN it documents the pipeline: public source → AI extraction → adaptation candidate → human review → synthetic ticket → golden expectation → evaluation

#### Scenario: Source reference fields are defined
- WHEN the AI extraction document is read
- THEN it defines source reference fields including source_id, source_name, source_type, source_language, source_usage_type, raw_data_committed, and license_note

#### Scenario: AI extraction candidate fields are defined
- WHEN the AI extraction document is read
- THEN it defines at least 10 extraction candidate fields covering issue summary, customer goal, scenario, risk signals, possible issue type, possible risk flags, evidence types, and adaptation notes

#### Scenario: AI vs Human responsibility matrix exists
- WHEN the AI extraction document is read
- THEN it contains a responsibility matrix specifying which fields AI can suggest and which fields require human confirmation

#### Scenario: Human review trigger rules are defined
- WHEN the AI extraction document is read
- THEN it lists at least 5 trigger conditions that mandate human review (including legal risk, privacy risk, and compensation demand)

#### Scenario: No-auto-send is architecture constraint
- WHEN the AI extraction document is read
- THEN `expected_no_auto_send` is documented as always true per architecture guarantee, not an AI-determined field

#### Scenario: Prohibited practices are documented
- WHEN the AI extraction document is read
- THEN it lists at least 5 prohibited practices including no raw external data commits, no AI-only golden labels, no real PII, no production claims, and no fake embedding overclaim

### Requirement: Phase 7 Baseline Audit
The system SHALL provide a baseline audit document at `docs/data/phase7_baseline_audit.md` that records the Phase 7 starting state before data expansion.

#### Scenario: Baseline audit contains ticket count
- WHEN `docs/data/phase7_baseline_audit.md` is read
- THEN it records the current eval ticket count (10)

#### Scenario: Baseline audit contains golden expectation count
- WHEN the baseline audit is read
- THEN it records the current golden expectation count (10)

#### Scenario: Baseline audit contains knowledge base count
- WHEN the baseline audit is read
- THEN it records the current knowledge record count (36)

#### Scenario: Baseline audit contains no-auto-send compliance values
- WHEN the baseline audit is read
- THEN it records no_auto_send_compliance from both CSV-mode (1.0) and pipeline-mode (0.5) reports

#### Scenario: Baseline audit contains Phase 7 targets
- WHEN the baseline audit is read
- THEN it lists Phase 7 targets: ~100 tickets, 80–120 knowledge records, 3 demo scenarios

### Requirement: Adaptation Candidate Workbook Template
The system SHALL provide an adaptation candidate workbook template at `docs/data/templates/adaptation_candidates.template.csv` for recording AI extraction candidates before human review.

#### Scenario: Template exists with header and example
- WHEN `docs/data/templates/adaptation_candidates.template.csv` is read
- THEN it contains a header row and exactly 1 example data row

#### Scenario: Template has required fields
- WHEN the template header is read
- THEN it includes candidate_id, source_id, source_name, source_usage_type, raw_issue_summary, customer_goal, product_or_service_context, issue_scenario, emotion_or_escalation_signal, possible_issue_type, possible_risk_flags, possible_severity, possible_must_human_review, possible_evidence_doc_types, missing_information, rewrite_needed, adapted_ticket_text, scenario_group, human_review_status, human_review_notes, ready_for_final_eval

#### Scenario: Example row uses synthetic data
- WHEN the template example row is read
- THEN it uses a synthetic refund+complaint scenario, not real customer data

### Requirement: AI Extraction Prompt Document
The system SHALL provide a reusable AI extraction prompt at `docs/data/ai_extraction_prompt.md` for converting source material into structured adaptation candidates.

#### Scenario: Prompt defines input format
- WHEN `docs/data/ai_extraction_prompt.md` is read
- THEN it specifies the input format with source_name, source_type, source_usage_type, and source_text_or_summary

#### Scenario: Prompt defines allowed values
- WHEN the prompt is read
- THEN it lists all 8 allowed issue_type values, all 8 allowed risk_flags values, and all 3 allowed evidence_doc_types values

#### Scenario: Prompt includes candidate-only rule
- WHEN the prompt is read
- THEN it states that AI output is candidate only and human review is required before final golden expectations

#### Scenario: Prompt includes JSON output schema
- WHEN the prompt is read
- THEN it includes a JSON output schema with all adaptation candidate fields

#### Scenario: Prompt includes example
- WHEN the prompt is read
- THEN it includes at least one example input and corresponding JSON output

#### Scenario: Prompt prohibits raw data copy
- WHEN the prompt is read
- THEN it states that adapted_ticket_text must be synthetic, not a verbatim copy of external data

#### Scenario: Prompt fixes no-auto-send as architecture constraint
- WHEN the prompt is read
- THEN it states that expected_no_auto_send is not decided by AI and is fixed as true for Phase 7

### Requirement: Adaptation Candidate Pool
The system SHALL provide an adaptation candidate pool at `data/eval/adaptation_candidates.csv` containing approximately 100 synthetic candidates generated via the AI-assisted extraction process.

#### Scenario: Candidate pool exists with header and data
- WHEN `data/eval/adaptation_candidates.csv` is read
- THEN it contains a header matching the template and 96–104 data rows

#### Scenario: All candidates are pending review
- WHEN every row in the candidate pool is checked
- THEN human_review_status is "pending" for all rows

#### Scenario: No candidate is ready for final eval
- WHEN every row in the candidate pool is checked
- THEN ready_for_final_eval is "false" for all rows

#### Scenario: All 8 issue types are represented
- WHEN the candidate pool is analyzed by possible_issue_type
- THEN each of the 8 issue types appears at least 8 times

#### Scenario: All 8 risk flags are covered
- WHEN the candidate pool is analyzed by possible_risk_flags
- THEN all 8 risk flag types appear at least once

#### Scenario: All 3 scenario groups have adequate coverage
- WHEN the candidate pool is analyzed by scenario_group
- THEN refund_complaint has at least 8 candidates
- AND privacy_account has at least 8 candidates
- AND invoice_payment has at least 8 candidates

#### Scenario: Candidate pool summary exists
- WHEN `docs/data/phase7_candidate_pool_summary.md` is read
- THEN it documents total count, distribution tables, and key candidates requiring human review

### Requirement: Data Spec Registration in OpenSpec Change
The system SHALL register the data sources and methodology spec under the `add-mvp-evidence-pack` OpenSpec change.

#### Scenario: Data spec file exists
- WHEN `openspec/changes/add-mvp-evidence-pack/specs/data/spec.md` is checked
- THEN it exists and contains ADDED requirements with Scenario blocks

## MODIFIED Requirements

(None — all data source and methodology requirements are new.)

## DELETED Requirements

(None)

## Data Sources

- All external source references are documented in `docs/data/evidence_pack_sources.md`.
- No raw external data is committed to the repository.
- All final eval tickets are synthetic/adapted, not raw-copied.

## Validation

- `openspec validate add-mvp-evidence-pack --strict` passes
- `openspec validate --all` passes (16/16)
- Quality gate passes
- All three documentation files exist under `docs/data/`
