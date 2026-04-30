# Tasks: Connect Retrieval to Intake-Risk Pipeline

## Batch A: Schema Extension

- [x] A.1 Create EvidenceCandidate Pydantic model in src/ticketpilot/schema/evidence.py:
  - Fields: doc_id (UUID), doc_type (DocType), source_id (UUID), source_table (str), chunk_id (UUID), content (str), score (float), rank (int, ge=1)
  - Validates that rank is at least 1
  - Validates that doc_type is a valid DocType enum value
- [x] A.2 Extend TicketOutput in src/ticketpilot/schema/ticket.py with evidence and trace:
  - Add optional evidence_candidates: list[EvidenceCandidate] = Field(default_factory=list)
  - Add optional retrieval_trace: RetrievalTrace or None = None
  - Maintain backward compatibility: existing fields unchanged
- [x] A.3 Export EvidenceCandidate from src/ticketpilot/schema/__init__.py
- [x] A.4 Verify EvidenceCandidate passes Pydantic validation with valid data
- [x] A.5 Verify EvidenceCandidate rejects invalid doc_type and rank below 1


## Batch B: Query Construction Logic

- [x] B.1 Create query_builder.py in src/ticketpilot/retrieval/query_builder.py with build_retrieval_query() function:
  - Signature: build_retrieval_query(normalized_text: str, intent: IntentClass, risk_flags: set[RiskFlag]) -> str
  - Combines normalized text + intent label + intent-derived business terms + risk-flag-derived terms
  - Returns a single query string suitable for hybrid_retrieval()
- [x] B.2 Implement intent-to-business-term mapping (Chinese terms):
  - REFUND -> (refund, return, policy)
  - RETURN_EXCHANGE -> (return, exchange, process)
  - ACCOUNT_ISSUE -> (account, login, password, security)
  - TECHNICAL_ISSUE -> (technical, error, bug)
  - PRODUCT_CONSULTING -> (product, consulting, spec, feature)
  - LOGISTICS -> (logistics, delivery, shipping)
  - COMPLAINT -> (complaint, rights, compensation, resolution)
  - OTHER -> no additional terms
- [x] B.3 Implement risk-flag-to-business-term mapping (Chinese terms):
  - COMPENSATION_RISK -> (compensation, settlement, amount)
  - LEGAL_RISK -> (legal, law, compliance, regulation)
  - PRIVACY_RISK -> (privacy, data, protection, information)
  - ACCOUNT_SECURITY_RISK -> (account security, fraud, verification, frozen)
  - POLICY_CONFLICT -> (policy, terms, rules, conflict)
  - Other flags -> no additional terms
- [x] B.4 Ensure query construction always includes normalized ticket text as the primary content
- [x] B.5 Deduplicate terms in the constructed query (no repeated words)


## Batch C: Pipeline Integration

- [x] C.1 Create evidence_mapper.py with map_fused_to_evidence() function:
  - Signature: map_fused_to_evidence(fused_results: list[FusedResult]) -> list[EvidenceCandidate]
  - Maps each FusedResult to an EvidenceCandidate
  - Looks up source_id and source_table from knowledge_chunks table for each chunk_id
  - Assigns rank based on position in fused_results list (1-based)
  - Maps rrf_score to score
  - Returns list of EvidenceCandidate sorted by rank
- [x] C.2 Create retrieve_evidence.py with retrieve_evidence() function:
  - Signature: retrieve_evidence(normalized_text, intent, risk_flags, top_k=10, doc_types=None) -> tuple[list[EvidenceCandidate], RetrievalTrace]
  - Calls build_retrieval_query() to construct query
  - Calls hybrid_retrieval() with the constructed query
  - Calls map_fused_to_evidence() to convert results
  - Returns (evidence_candidates, retrieval_trace)
  - Always returns a RetrievalTrace even when no results found
- [x] C.3 Update pipeline.py intake_risk_pipeline():
  - Add Stage 4: after risk assessment, call retrieve_evidence()
  - When evidence_candidates is empty, add INSUFFICIENT_EVIDENCE to risk flags
  - Preserve must_human_review from risk assessment (never downgrade)
  - Return TicketOutput with evidence_candidates and retrieval_trace
  - Graceful degradation: if retrieval raises, still return output with empty evidence and INSUFFICIENT_EVIDENCE flag
  - Update docstring to document the 4-stage pipeline
- [x] C.4 Update __init__.py exports to include new functions and schemas


## Batch D: Tests

- [x] D.1 Create tests/unit/test_evidence_schema.py:
  - Test EvidenceCandidate creation with valid data
  - Test EvidenceCandidate rejects invalid doc_type
  - Test EvidenceCandidate rejects rank below 1
  - Test EvidenceCandidate with all fields populated
- [x] D.2 Create tests/unit/test_query_builder.py:
  - Test query includes normalized text
  - Test query includes intent label
  - Test intent-to-business-term mapping for all 8 intents
  - Test risk-flag-to-business-term mapping
  - Test combined query (text + intent + multiple risk flags)
  - Test OTHER intent produces minimal query (text only)
  - Test deduplication of repeated terms
  - Test empty text produces valid query (intent terms only)
- [x] D.3 Create tests/unit/test_evidence_mapper.py:
  - Test map_fused_to_evidence with non-empty fused results
  - Test evidence candidates have correct doc_id, doc_type, chunk_id, content, score, rank
  - Test source_id and source_table are populated (mock DB lookup)
  - Test map_fused_to_evidence with empty list returns empty list
  - Test rank ordering is preserved (rank 1 equals highest score)
- [x] D.4 Create tests/unit/test_retrieve_evidence.py:
  - Test retrieve_evidence constructs query and calls hybrid_retrieval (mock)
  - Test retrieve_evidence returns evidence candidates with expected fields
  - Test retrieve_evidence always returns a RetrievalTrace
  - Test retrieve_evidence when hybrid_retrieval returns empty results
  - Test doc_types filter is passed through to hybrid_retrieval
- [x] D.5 Create tests/unit/test_pipeline_retrieval.py:
  - Test pipeline with mocked retrieval returns TicketOutput with evidence
  - Test pipeline adds INSUFFICIENT_EVIDENCE when retrieval returns empty
  - Test pipeline preserves must_human_review=true when retrieval succeeds
  - Test pipeline preserves must_human_review=true when retrieval returns empty
  - Test pipeline graceful degradation when retrieval raises exception
  - Test pipeline output includes retrieval_trace
- [x] D.6 Create tests/integration/test_pipeline_retrieval_integration.py:
  - Test full pipeline against live DB: Chinese refund query returns FAQ or POLICY evidence
  - Test full pipeline against live DB: Chinese account-hacked query returns relevant evidence
  - Test full pipeline: nonsense query returns empty evidence with INSUFFICIENT_EVIDENCE flag
  - Test full pipeline: high-risk ticket preserves must_human_review=true
  - Test full pipeline: LOW_CONFIDENCE classification does not block retrieval
  - Verify RetrievalTrace is present and has expected fields in integration output


## Batch E: Documentation and Quality Gate

- [x] E.1 Update docs/changelog.md with connect-retrieval-to-pipeline entry:
  - Date: 2026-04-30
  - Summary: wired hybrid retrieval into intake-risk pipeline as Stage 4
  - Key additions: query builder, evidence mapper, extended TicketOutput
  - Test counts: unit and integration
- [x] E.2 Run quality gate: bash scripts/run_quality_gate.sh
- [x] E.3 Verify all unit tests pass
- [x] E.4 Verify all integration tests pass against live DB
- [x] E.5 Verify openspec validate still passes for existing changes (backward compatible)
- [x] E.6 Update docs/phase_status.md if it exists

## Acceptance Criteria Verification

- [x] AC1: Pipeline includes 4 stages (intake -> classify -> risk -> retrieve)
- [x] AC2: Output includes evidence_candidates with 8 required fields (doc_id, doc_type, source_id, source_table, chunk_id, content, score, rank)
- [x] AC3: RetrievalTrace included in pipeline output with query, keyword_results, vector_results, fused_results, final_evidence_ids
- [x] AC4: No evidence triggers INSUFFICIENT_EVIDENCE flag in risk assessment
- [x] AC5: must_human_review is preserved regardless of retrieval outcome
- [x] AC6: Query is built from normalized text + intent label + risk flag business terms
- [x] AC7: Pipeline handles retrieval failure with graceful degradation (still returns output)
- [x] AC8: Evidence candidates sorted by score descending (highest score equals rank 1)
- [x] AC9: All existing 150 unit tests and 49 integration tests still pass (no regression)
- [x] AC10: Quality gate passes
