## ADDED Requirements


### Requirement: Pipeline includes evidence retrieval
The intake-risk pipeline SHALL include a retrieve_evidence stage that calls hybrid_retrieval after risk assessment, producing evidence candidates for downstream review.

#### Scenario: Evidence retrieved for a normal ticket
- GIVEN a normalized ticket with text containing a refund request and intent REFUND
- WHEN the pipeline processes the ticket
- THEN the output includes evidence_candidates with at least one FAQ or POLICY result

#### Scenario: No evidence triggers insufficient_evidence flag
- GIVEN a ticket with text that matches no knowledge documents
- WHEN the pipeline processes the ticket
- THEN the output risk assessment includes INSUFFICIENT_EVIDENCE flag

#### Scenario: Retrieval runs after risk assessment
- GIVEN any ticket
- WHEN the pipeline processes the ticket
- THEN the retrieve_evidence stage runs AFTER risk assessment (Stage 4)
- AND the classification and risk_assessment fields are populated before retrieval

#### Scenario: Query is built from ticket state
- GIVEN a normalized ticket with text, intent classification, and risk flags
- WHEN the retrieve_evidence stage executes
- THEN the retrieval query includes the normalized ticket text
- AND the query includes terms derived from the intent classification
- AND the query includes terms derived from active risk flags


### Requirement: Evidence candidates have required fields
Each evidence candidate SHALL include doc_id, doc_type, source_id, source_table, chunk_id, content, score, and rank.

#### Scenario: Evidence candidate contains all required fields
- GIVEN retrieval returns fused results
- WHEN the results are mapped to evidence candidates
- THEN each candidate has doc_id of type UUID
- AND doc_type is a valid DocType enum value (FAQ, POLICY, or CASE)
- AND source_id of type UUID is present
- AND source_table is a non-empty string identifying the source table
- AND chunk_id of type UUID is present
- AND content is a non-empty string
- AND score is a float representing the RRF fusion score
- AND rank is an integer >= 1 representing position in sorted results

#### Scenario: Evidence candidates are sorted by score descending
- GIVEN multiple evidence candidates
- WHEN they are included in the pipeline output
- THEN they are sorted by score in descending order
- AND rank 1 corresponds to the highest score

#### Scenario: Empty results produce empty evidence list
- GIVEN retrieval returns no fused results
- WHEN the results are mapped to evidence candidates
- THEN evidence_candidates is an empty list


### Requirement: Retrieval trace is preserved
The pipeline output SHALL include the RetrievalTrace for audit and debugging.

#### Scenario: Retrieval trace included when evidence found
- GIVEN retrieval returns fused results
- WHEN the pipeline completes
- THEN the output includes a retrieval_trace field
- AND retrieval_trace is not None
- AND retrieval_trace contains the original query
- AND retrieval_trace contains keyword_results
- AND retrieval_trace contains vector_results
- AND retrieval_trace contains fused_results
- AND retrieval_trace contains final_evidence_ids

#### Scenario: Retrieval trace included when no evidence found
- GIVEN retrieval returns no fused results
- WHEN the pipeline completes
- THEN the output includes a retrieval_trace field
- AND retrieval_trace is not None
- AND retrieval_trace.fused_results is an empty list
- AND retrieval_trace.final_evidence_ids is an empty list

#### Scenario: Retrieval trace includes latency information
- GIVEN the pipeline runs the retrieve_evidence stage
- WHEN the retrieval completes
- THEN retrieval_trace includes keyword_latency_ms
- AND retrieval_trace includes vector_latency_ms
- AND retrieval_trace includes fusion_latency_ms
- AND retrieval_trace includes total_latency_ms


### Requirement: must_human_review is preserved
When risk assessment sets must_human_review=true, the pipeline output SHALL preserve this value regardless of retrieval outcome.

#### Scenario: High-risk ticket keeps must_human_review after successful retrieval
- GIVEN risk assessment sets must_human_review=true
- AND retrieval returns evidence candidates
- WHEN the pipeline completes
- THEN the output risk_assessment.must_human_review is true

#### Scenario: High-risk ticket keeps must_human_review after empty retrieval
- GIVEN risk assessment sets must_human_review=true
- AND retrieval returns no evidence
- WHEN the pipeline completes
- THEN the output risk_assessment.must_human_review is true
- AND the risk flags include INSUFFICIENT_EVIDENCE

#### Scenario: Low-risk ticket must_human_review is not upgraded by retrieval
- GIVEN risk assessment sets must_human_review=false
- AND retrieval succeeds with evidence
- WHEN the pipeline completes
- THEN the output risk_assessment.must_human_review remains false

### Requirement: Pipeline graceful degradation on retrieval failure
The pipeline SHALL handle retrieval errors gracefully and return a valid output with empty evidence.

#### Scenario: Retrieval raises an exception
- GIVEN the hybrid_retrieval call raises an exception
- WHEN the pipeline processes the ticket
- THEN the output is still returned (not an exception)
- AND evidence_candidates is an empty list
- AND the risk flags include INSUFFICIENT_EVIDENCE
- AND retrieval_trace is None or indicates the failure

#### Scenario: Retrieval degradation does not affect prior stages
- GIVEN retrieval fails
- WHEN the pipeline output is inspected
- THEN classification is still populated
- AND risk_assessment is still populated
- AND normalized_ticket is still populated


### Requirement: Query construction logic
The retrieve_evidence stage SHALL construct a retrieval query from the normalized ticket text, intent classification, and risk flag business terms.

#### Scenario: Query always includes normalized text
- GIVEN a normalized ticket with text content
- WHEN the retrieval query is constructed
- THEN the query string contains the normalized text as its primary content

#### Scenario: Intent adds business terms to query
- GIVEN a ticket classified as REFUND
- WHEN the retrieval query is constructed
- THEN the query includes terms commonly associated with refund intents (e.g., refund, return, policy in Chinese context)

#### Scenario: Risk flags add relevant terms to query
- GIVEN a ticket with COMPENSATION_RISK flag
- WHEN the retrieval query is constructed
- THEN the query includes terms associated with compensation (e.g., compensation, settlement, amount in Chinese context)

#### Scenario: Multiple risk flags combine terms
- GIVEN a ticket with both LEGAL_RISK and COMPENSATION_RISK flags
- WHEN the retrieval query is constructed
- THEN the query includes terms from both flag categories

#### Scenario: OTHER intent produces minimal query
- GIVEN a ticket classified as OTHER with no risk flags
- WHEN the retrieval query is constructed
- THEN the query consists primarily of the normalized text
- AND no intent-derived terms are added

#### Scenario: Constructed terms are deduplicated
- GIVEN overlapping terms from intent and risk flag mappings
- WHEN the retrieval query is constructed
- THEN duplicate terms are removed from the final query string

### Requirement: EvidenceCandidate schema is Pydantic-validated
The EvidenceCandidate model SHALL use Pydantic for validation of all fields.

#### Scenario: Valid data passes validation
- GIVEN a dictionary with all required EvidenceCandidate fields
- WHEN an EvidenceCandidate is instantiated
- THEN the instance is created successfully with all fields populated

#### Scenario: Invalid doc_type is rejected
- GIVEN data with doc_type set to an invalid value
- WHEN an EvidenceCandidate is instantiated
- THEN a Pydantic ValidationError is raised

#### Scenario: Rank below 1 is rejected
- GIVEN data with rank set to 0 or negative
- WHEN an EvidenceCandidate is instantiated
- THEN a Pydantic ValidationError is raised
