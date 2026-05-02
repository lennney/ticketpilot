# drafting Specification

## Purpose
TBD - created by archiving change add-evidence-draft-generation. Update Purpose after archive.
## Requirements
### Requirement: Citation Schema
The system SHALL define a Citation Pydantic model with fields: chunk_id (UUID), doc_id (UUID), doc_type (DocType), source_table (str), source_id (UUID), evidence_excerpt (str, max 200 chars), claim_supported (bool).

#### Scenario: Valid Citation constructs successfully
- **WHEN** Citation is created with valid chunk_id, doc_id, doc_type, source_table, source_id, evidence_excerpt
- **THEN** it passes Pydantic validation and all fields are populated correctly

#### Scenario: Citation claim_supported defaults to False
- **WHEN** Citation is created without claim_supported
- **THEN** claim_supported defaults to False

#### Scenario: Citation invalid doc_type is rejected
- **WHEN** Citation is created with doc_type set to an invalid enum value
- **THEN** Pydantic ValidationError is raised

#### Scenario: Citation evidence_excerpt over 200 chars is rejected
- **WHEN** Citation is created with evidence_excerpt longer than 200 characters
- **THEN** Pydantic ValidationError is raised

### Requirement: DraftReply Schema
The system SHALL define DraftReply as a Pydantic model with fields: ticket_id (str), draft_text (str), citations (list[Citation]), evidence_used (list[Citation]), unsupported_claims (list[str]), missing_information (list[str]), confidence (float, 0.0 to 1.0), must_human_review (bool), fallback_reason (str | None), generation_trace (dict | None).

#### Scenario: Valid DraftReply constructs successfully
- **WHEN** DraftReply is created with valid fields including a non-empty citations list
- **THEN** it passes Pydantic validation and serializes to JSON

#### Scenario: DraftReply empty citations list is allowed
- **WHEN** DraftReply is created with an empty citations list
- **THEN** it passes Pydantic validation and citations is an empty list

#### Scenario: DraftReply confidence defaults to 0.0
- **WHEN** DraftReply is created without confidence
- **THEN** confidence defaults to 0.0

#### Scenario: DraftReply must_human_review defaults to False
- **WHEN** DraftReply is created without must_human_review
- **THEN** must_human_review defaults to False

#### Scenario: DraftReply confidence below 0.0 is rejected
- **WHEN** DraftReply is created with confidence=-0.1
- **THEN** Pydantic ValidationError is raised

#### Scenario: DraftReply confidence above 1.0 is rejected
- **WHEN** DraftReply is created with confidence=1.5
- **THEN** Pydantic ValidationError is raised

### Requirement: DraftGenerationTrace Schema
The system SHALL define DraftGenerationTrace as a Pydantic model with fields: ticket_id (str), evidence_used (list[Citation]), evidence_count (int), total_evidence_available (int), confidence_score (float), unsupported_claims (list[str]), human_review_required (bool), fallback_reason (str | None), created_at (datetime).

#### Scenario: Valid DraftGenerationTrace constructs successfully
- **WHEN** DraftGenerationTrace is created with valid fields
- **THEN** it passes Pydantic validation and all fields are populated

#### Scenario: DraftGenerationTrace fallback_reason defaults to None
- **WHEN** DraftGenerationTrace is created without fallback_reason
- **THEN** fallback_reason is None

#### Scenario: DraftGenerationTrace human_review_required defaults to False
- **WHEN** DraftGenerationTrace is created without human_review_required
- **THEN** human_review_required defaults to False

#### Scenario: DraftGenerationTrace confirmed in bounds
- **WHEN** DraftGenerationTrace is created with evidence_used containing fewer or equal items than total_evidence_available
- **THEN** all fields are accepted without error

#### Scenario: DraftGenerationTrace JSON serialization
- **WHEN** DraftGenerationTrace is serialized via model_dump_json()
- **THEN** output JSON contains all audit-relevant fields including confidence_score, unsupported_claims, and fallback_reason

### Requirement: AbstractDraftProvider Interface
The system SHALL define AbstractDraftProvider as an abstract interface with method: generate(evidence_candidates: list[EvidenceCandidate], risk_assessment: RiskAssessment, classification: ClassificationResult, normalized_text: str) -> DraftReply.

#### Scenario: AbstractDraftProvider is an abstract class
- **WHEN** AbstractDraftProvider is inspected
- **THEN** it is an abstract base class and cannot be instantiated directly

#### Scenario: AbstractDraftProvider declares generate signature
- **WHEN** AbstractDraftProvider is inspected for abstract methods
- **THEN** it has generate method with signature (evidence_candidates: list[EvidenceCandidate], risk_assessment: RiskAssessment, classification: ClassificationResult, normalized_text: str) -> DraftReply

#### Scenario: Non-abstract subclass without generate raises TypeError
- **WHEN** a class that inherits from AbstractDraftProvider does not implement generate
- **THEN** instantiating the class raises TypeError

#### Scenario: Subclass with correct generate instantiates
- **WHEN** a class that inherits from AbstractDraftProvider implements generate
- **THEN** the class instantiates successfully and is an instance of AbstractDraftProvider

### Requirement: FakeDraftProvider
The system SHALL implement FakeDraftProvider as a deterministic, template-based provider that generates draft replies from evidence candidates without calling any real LLM.

#### Scenario: FakeDraftProvider constructs from evidence
- **WHEN** FakeDraftProvider.generate is called with a non-empty evidence list and valid risk/classification/text inputs
- **THEN** returns DraftReply with draft_text containing Chinese text that references evidence content

#### Scenario: FakeDraftProvider output is deterministic
- **WHEN** FakeDraftProvider.generate is called twice with identical inputs
- **THEN** both DraftReply outputs are identical (same draft_text, same citations, same confidence)

#### Scenario: FakeDraftProvider creates citations from evidence
- **WHEN** FakeDraftProvider.generate is called with evidence containing 3 candidates
- **THEN** DraftReply.citations contains exactly 3 Citation objects
- **AND** each Citation.doc_id matches the corresponding EvidenceCandidate.doc_id
- **AND** each Citation.chunk_id matches the corresponding EvidenceCandidate.chunk_id
- **AND** each Citation.evidence_excerpt is a non-empty string from the evidence content

#### Scenario: FakeDraftProvider sets confidence based on evidence
- **WHEN** FakeDraftProvider.generate is called with high-scoring evidence
- **THEN** DraftReply.confidence is proportional to the number and scores of evidence items

#### Scenario: FakeDraftProvider does not call any external API
- **WHEN** FakeDraftProvider.generate is called
- **THEN** no HTTP requests, no LLM calls, and no database queries are made

#### Scenario: FakeDraftProvider evidence_count equals 0 with empty evidence
- **WHEN** FakeDraftProvider.generate is called with empty evidence list
- **THEN** returns DraftReply with unsupported_claims=False
- **AND** DraftReply.confidence is 0.0
- **AND** DraftReply.citations is an empty list

### Requirement: Citation-Aware Reply
The system SHALL ensure every substantive claim in the draft reply maps to at least one Citation with evidence_excerpt from the supporting evidence.

#### Scenario: Citation maps claim to evidence excerpt
- **WHEN** DraftReply is generated from evidence with content "退货需要在7天内申请"
- **THEN** the draft_text contains related claim about 7-day return window
- **AND** at least one Citation.evidence_excerpt includes "7天内申请" or equivalent text

#### Scenario: Multiple citations for multi-evidence claims
- **WHEN** DraftReply is generated from FAQ evidence about policy and Case evidence about precedent
- **THEN** the draft_text includes claims from both sources
- **AND** citations include entries from both FAQ and CASE doc_types

#### Scenario: Citation rank preserves original evidence ranking
- **WHEN** DraftReply.citations are created from evidence sorted by rank
- **THEN** each Citation.rank matches the original EvidenceCandidate.rank value

#### Scenario: Citation doc_type matches evidence source
- **WHEN** DraftReply is generated with evidence from POLICY documents
- **THEN** all Citation.doc_type values equal DocType.POLICY

### Requirement: Unsupported Claim Guard
The system SHALL implement CitationValidator that detects claims in the draft reply that are not backed by any citation.

#### Scenario: Validator passes fully cited reply
- **WHEN** CitationValidator.validate is called on a DraftReply where all claims have corresponding citations
- **THEN** returns True (no issues)
- **AND** DraftReply.unsupported_claims is an empty list

#### Scenario: Validator flags unsupported claim
- **WHEN** CitationValidator.validate is called on a DraftReply with a claim not found in any citation evidence_excerpt
- **THEN** returns False (issue detected)
- **AND** DraftReply.unsupported_claims is non-empty

#### Scenario: Validator identifies exact unsupported sentences
- **WHEN** CitationValidator.validate detects an unsupported claim
- **THEN** it returns details identifying which sentence or segment is unsupported

#### Scenario: Validator on fallback-only text
- **WHEN** CitationValidator.validate is called on the safe fallback message with empty citations
- **THEN** returns False (the fallback text contains disclaimer language that matches claim-keyword patterns)
- **AND** the issues list contains the detection detail
- **NOTE** generate_draft() clears these expected issues before returning the final DraftReply

#### Scenario: Validator does not modify the DraftReply
- **WHEN** CitationValidator.validate is called
- **THEN** the DraftReply.draft_text and DraftReply.citations are not mutated

### Requirement: No-Evidence Fallback
The system SHALL generate a safe fallback draft reply that acknowledges the lack of evidence when the evidence list is empty.

#### Scenario: Fallback reply acknowledges no evidence
- **WHEN** DraftReply is generated with an empty evidence list
- **THEN** draft_text contains a Chinese message indicating no relevant knowledge was found (e.g., "未找到相关知识库匹配信息，建议人工核实后回复")
- **AND** DraftReply.unsupported_claims is False (safe message makes no substantive claims)
- **AND** DraftReply.confidence is 0.0
- **AND** DraftReply.citations is an empty list

#### Scenario: Fallback trace records reason
- **WHEN** fallback is triggered due to no evidence
- **THEN** DraftGenerationTrace.fallback_reason equals "no_evidence"
- **AND** len(DraftGenerationTrace.evidence_used) is 0
- **AND** DraftGenerationTrace.evidence_count is 0
- **AND** DraftGenerationTrace.total_evidence_available is 0
- **AND** DraftGenerationTrace.confidence_score is 0.0
- **AND** DraftGenerationTrace.unsupported_claims is False
- **AND** DraftGenerationTrace.human_review_required is True

#### Scenario: Fallback reply is deterministic
- **WHEN** fallback is triggered twice with the same ticket
- **THEN** both fallback replies have identical draft_text

#### Scenario: Fallback is in Chinese
- **WHEN** the no-evidence fallback reply is generated
- **THEN** draft_text is entirely in Chinese

### Requirement: High-Risk Fallback
The system SHALL still generate a draft reply when must_human_review is True, but mark the trace accordingly to require human review.

#### Scenario: High-risk generates reply with review flag
- **WHEN** DraftReply is generated with must_human_review=True
- **THEN** DraftReply is generated successfully (not skipped)
- **AND** DraftGenerationTrace.human_review_required is True

#### Scenario: High-risk reply has confidence ceiling
- **WHEN** DraftReply is generated with must_human_review=True
- **THEN** DraftReply.confidence does not exceed 0.5

#### Scenario: High-risk with evidence still generates citations
- **WHEN** DraftReply is generated with must_human_review=True and non-empty evidence
- **THEN** DraftReply.citations is populated from evidence
- **AND** DraftGenerationTrace.evidence_used equals len(evidence)

#### Scenario: High-risk trace preserves original evidence count
- **WHEN** DraftReply is generated with must_human_review=True
- **THEN** DraftGenerationTrace.total_evidence_available equals the number of evidence candidates passed to the provider

#### Scenario: Low-risk without evidence still triggers no-evidence fallback
- **WHEN** DraftReply is generated with must_human_review=False and empty evidence
- **THEN** DraftGenerationTrace.fallback_reason equals "no_evidence"
- **AND** DraftGenerationTrace.human_review_required is True

#### Scenario: High-risk fallback does not require a separate code path
- **WHEN** must_human_review=True and evidence is non-empty
- **THEN** FakeDraftProvider uses the same template logic as low-risk
- **AND** the only difference is the confidence ceiling and human_review_required flag

### Requirement: Confidence Scoring
The system SHALL calculate draft confidence score based on evidence coverage, where confidence = (evidence_used / max(1, total_evidence)) * avg_normalized_score.

#### Scenario: Full evidence coverage yields high confidence
- **WHEN** all available evidence is used and average score is high (>= 0.8)
- **THEN** DraftReply.confidence is >= 0.7

#### Scenario: Partial evidence coverage yields proportional confidence
- **WHEN** only 3 out of 10 evidence items are used
- **THEN** DraftReply.confidence is proportionally lower than full coverage

#### Scenario: Zero evidence yields zero confidence
- **WHEN** no evidence is available
- **THEN** DraftReply.confidence is 0.0

#### Scenario: Low-score evidence yields lower confidence
- **WHEN** evidence items all have scores below 0.3
- **THEN** DraftReply.confidence is below 0.3

#### Scenario: Confidence is clamped to [0.0, 1.0] range
- **WHEN** calculated confidence exceeds 1.0 due to score weighting
- **THEN** DraftReply.confidence is clamped to 1.0

#### Scenario: High-risk adds confidence ceiling
- **WHEN** must_human_review=True and calculated confidence would be 0.8
- **THEN** DraftReply.confidence is capped at 0.5

### Requirement: Chinese Language Output
The system SHALL generate draft replies in Chinese for all inputs, including fallback messages.

#### Scenario: Normal evidence-based reply is in Chinese
- **WHEN** DraftReply is generated from evidence with Chinese content
- **THEN** draft_text is entirely in Chinese

#### Scenario: No-evidence fallback is in Chinese
- **WHEN** fallback reply is generated due to empty evidence
- **THEN** draft_text is in Chinese

#### Scenario: High-risk reply is in Chinese
- **WHEN** DraftReply is generated for a high-risk ticket with evidence
- **THEN** draft_text is in Chinese

#### Scenario: All citations contain Chinese evidence_excerpt
- **WHEN** DraftReply has citations
- **THEN** each Citation.evidence_excerpt is in Chinese

