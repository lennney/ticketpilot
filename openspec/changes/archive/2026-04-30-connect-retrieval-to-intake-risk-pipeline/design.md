## Context

TicketPilot is a Chinese customer support ticket triage and evidence-grounded reply Copilot. This change connects the already-built retrieval system (Stage 1B) to the main intake-risk pipeline (Stages 1-3), adding retrieve_evidence as Stage 4.

**What exists today (implemented and verified):**

Stages 1-3 -- Intake + Classification + Risk Assessment:

RawTicket -> intake_pipeline() -> NormalizedTicket -> IntentClassifier.classify() -> ClassificationResult -> RiskAssessor.assess() -> RiskAssessment -> TicketOutput

- intake_risk_pipeline() in src/ticketpilot/pipeline.py chains stages 1-3.
- Each stage has try/except graceful degradation: fallback values are returned on failure.
- TicketOutput aggregates: ticket_id, raw_ticket, normalized_ticket, classification, risk_assessment, output_at.

Stage 1B -- Retrieval (built, tested, disconnected from main pipeline):

query text -> FakeEmbeddingProvider.embed() -> [keyword_search(), vector_search()] -> [KeywordResult[], VectorResult[]] -> rrf_fusion() -> FusedResult[] -> RetrievalTrace

- hybrid_retrieval() in src/ticketpilot/retrieval/pipeline.py orchestrates full retrieval.
- Supports optional doc_types filter (list of DocType: FAQ, POLICY, CASE).
- Produces RetrievalTrace with full explainability: keyword results, vector results, per-ranker RRF contributions, latency breakdown, HNSW params.
- Underlying data: 12 FAQ, 12 Policy, 12 Case documents across 3 source tables; 36 chunks in unified knowledge_chunks table with HNSW and FTS indexes.

**What does NOT exist:**
- No connection between the retrieval system and the ticket pipeline.
- No evidence field on TicketOutput.
- No query construction logic that transforms ticket state into a retrieval query.
- No intent-to-doc-type filtering.

**Constraints:**
- No real LLM API calls
- No reply generation
- No Streamlit UI integration
- No LangGraph workflow nodes
- No Langfuse/Ragas
- No real embedding provider changes
- No reranker
- The retrieval module (src/ticketpilot/retrieval/) must remain unchanged -- it works and is independently tested.

## Goals / Non-Goals

**Goals:**
- Build a query construction function that produces a Chinese retrieval query from ticket state (normalized text, intent label, risk flags).
- Add retrieve_evidence as Stage 4 in intake_risk_pipeline() so the full pipeline is: intake -> classify -> assess_risk -> retrieve_evidence.
- Extend TicketOutput with optional evidence fields: a list of EvidenceCandidate items and the full RetrievalTrace.
- Apply intent-to-doc-type filtering so retrieval only searches relevant knowledge domains.
- Graceful degradation: if retrieval fails or returns no results, add INSUFFICIENT_EVIDENCE flag, return empty candidates list, preserve must_human_review, and always include a trace.
- Keep the retrieval module unchanged -- zero modifications to src/ticketpilot/retrieval/.

**Non-Goals:**
- Reply generation (handled in a later vertical slice).
- Evidence ranking or reranking beyond RRF fusion.
- Persisting traces to the database (produce them in-memory; persistence is a future concern).
- Multilingual query expansion (Chinese + English) beyond simple concatenation.
- Query rewriting based on risk flags (simple concatenation only).
- Agentic or iterative retrieval -- single-shot retrieval only.
- Streamlit UI for evidence review.

## Architecture

### Data Flow Diagram

```
                          intake_risk_pipeline()
  +----------------------------------------------------------------------------+
  |                                                                            |
  |  RawTicket                                                                |
  |     |                                                                      |
  |     v                                                                      |
  |  +-----------------+                                                       |
  |  | Stage 1: Intake | -> NormalizedTicket                                   |
  |  +-----------------+                                                       |
  |     |                                                                      |
  |     v                                                                      |
  |  +----------------------+                                                  |
  |  | Stage 2: Classify    | -> ClassificationResult (intent + confidence)    |
  |  +----------------------+                                                  |
  |     |                                                                      |
  |     v                                                                      |
  |  +---------------------------+                                             |
  |  | Stage 3: Risk Assessment  | -> RiskAssessment (flags + severity)        |
  |  +---------------------------+                                             |
  |     |                                                                      |
  |     |  NormalizedTicket + ClassificationResult + RiskAssessment            |
  |     |                                                                      |
  |     v                                                                      |
  |  +----------------------------------------+                               |
  |  | Stage 4: Retrieve Evidence (NEW)       |                               |
  |  |                                        |                               |
  |  |  1. build_retrieval_query()            |                               |
  |  |     Input:  normalized text            |                               |
  |  |             intent enum                |                               |
  |  |             risk flags                 |                               |
  |  |     Output: Chinese query string       |                               |
  |  |                                        |                               |
  |  |  2. map_intent_to_doc_types()          |                               |
  |  |     Input:  intent enum                |                               |
  |  |     Output: list[DocType]              |                               |
  |  |                                        |                               |
  |  |  3. hybrid_retrieval(query, doc_types) |                               |
  |  |     Input:  query string               |                               |
  |  |             doc_types filter           |                               |
  |  |     Output: RetrievalTrace             |                               |
  |  |                                        |                               |
  |  |  4. extract_evidence_candidates()      |                               |
  |  |     Input:  FusedResult[]              |                               |
  |  |             score threshold            |                               |
  |  |     Output: list[EvidenceCandidate]    |                               |
  |  +----------------------------------------+                               |
  |     |                                                                      |
  |     v                                                                      |
  |  +--------------------------------------------------+                      |
  |  | TicketOutput (extended with evidence fields)      |                      |
  |  |   ticket_id, raw_ticket, normalized_ticket,       |                      |
  |  |   classification, risk_assessment,                |                      |
  |  |   evidence_candidates: list[EvidenceCandidate],   |  <-- NEW            |
  |  |   retrieval_trace: RetrievalTrace | None,         |  <-- NEW            |
  |  |   output_at                                      |                      |
  |  +--------------------------------------------------+                      |
  |                                                                            |
  +----------------------------------------------------------------------------+
```

### Component Interactions

```
pipeline.py (intake_risk_pipeline)
  |
  +-- intake.pipeline.pipeline()          # Stage 1 (unchanged)
  +-- classification.classifier           # Stage 2 (unchanged)
  +-- risk.assessor.RiskAssessor          # Stage 3 (unchanged)
  |
  +-- [NEW] build_retrieval_query()       # lives in retrieval/query_builder.py
  |      Input:  normalized_text, intent, risk_flags
  |      Output: str (Chinese query)
  |
  +-- [NEW] map_intent_to_doc_types()     # lives in pipeline.py
  |      Input:  IntentClass
  |      Output: list[DocType]
  |
  +-- retrieval.pipeline.hybrid_retrieval()  # Stage 4 core (unchanged)
  |      Input:  query (str), doc_types (list[DocType] | None)
  |      Output: RetrievalTrace
  |
  +-- [NEW] extract_evidence_candidates() # lives in retrieval/evidence_mapper.py
  |      Input:  fused_results: list[FusedResult], min_score: float
  |      Output: list[EvidenceCandidate]
  |
  +-- [MODIFIED] TicketOutput
         Adds: evidence_candidates, retrieval_trace (optional fields)
```

**Module boundaries (summary):**

| Module | Path | Changed? | Rationale |
|--------|------|----------|-----------|
| pipeline.py | src/ticketpilot/pipeline.py | **Yes** | New Stage 4 orchestration, map_intent_to_doc_types |
| schema/ticket.py | src/ticketpilot/schema/ticket.py | **Yes** | Extend TicketOutput with evidence fields |
| schema/evidence.py | src/ticketpilot/schema/evidence.py | **Yes (new)** | EvidenceCandidate boundary schema |
| retrieval/query_builder.py | src/ticketpilot/retrieval/query_builder.py | **Yes (new)** | Query construction with intent/risk-flag business term mappings |
| retrieval/evidence_mapper.py | src/ticketpilot/retrieval/evidence_mapper.py | **Yes (new)** | FusedResult → EvidenceCandidate adapter |
| retrieval/pipeline.py | src/ticketpilot/retrieval/pipeline.py | **No** | Existing hybrid_retrieval() called as-is |
| retrieval/traces.py | src/ticketpilot/retrieval/traces.py | **No** | FusedResult, RetrievalTrace consumed unchanged |
| retrieval/schema/knowledge.py | src/ticketpilot/retrieval/schema/knowledge.py | **No** | DocType enum consumed unchanged |
| classification/ | src/ticketpilot/classification/ | **No** | IntentClass consumed unchanged |
| risk/ | src/ticketpilot/risk/ | **No** | RiskAssessment consumed unchanged |
| intake/ | src/ticketpilot/intake/ | **No** | NormalizedTicket consumed unchanged |

## Query Construction Strategy

### Decision: Simple concatenation template

The query is built by joining the ticket's normalized text with the Chinese label of the classified intent. Risk flags are NOT appended to the query in the initial implementation -- they are used only for intent-to-doc-type mapping and the resulting RiskFlag.INSUFFICIENT_EVIDENCE flag.

### Template

```
{normalized_text} {intent_chinese_label}
```

Example:
- Normalized text: "我在3月15日购买的耳机有质量问题，申请退款"
- Intent: IntentClass.REFUND
- Result query: "我在3月15日购买的耳机有质量问题，申请退款 退款"

### Intent-to-Chinese-Label Mapping

| IntentClass | Chinese Label |
|-------------|---------------|
| REFUND | 退款 |
| RETURN_EXCHANGE | 退货 |
| ACCOUNT_ISSUE | 账号问题 |
| TECHNICAL_ISSUE | 技术问题 |
| PRODUCT_CONSULTING | 产品咨询 |
| LOGISTICS | 物流 |
| COMPLAINT | 投诉 |
| OTHER | (empty -- no label appended) |

### Edge Cases

1. **Empty normalized text** (intake failure): Use only the Chinese intent label as the query. If intent is OTHER, use an empty string and skip retrieval entirely (return empty candidates).
2. **Intent is OTHER**: Append no label; use normalized text alone.
3. **Very short text** (< 3 characters): Use intent label only, since the text is likely noise.

### Trade-offs

- **Simple vs. template-based**: Starting with simple concatenation. A template like "用户询问关于{intent_label}: {text}" could be tested later but adds noise from wrapper words that dilute the semantic signal.
- **Risk flags in query**: Not included initially. Adding risk-flag keywords (e.g., append "赔偿 法律" when compensation_risk or legal_risk flags are present) would broaden recall but also risks query drift. Deferred to a later iteration once retrieval quality metrics are available.
- **FTS compatibility**: Chinese text benefits from simple concatenation because PostgreSQL's to_tsvector('simple', content) tokenizes on whitespace. Appending the intent label as a separate term ensures exact keyword matches on the label itself.

## Schema Changes

### Modified: TicketOutput

```python
class TicketOutput(BaseModel):
    ticket_id: str
    raw_ticket: RawTicket
    normalized_ticket: NormalizedTicket
    classification: ClassificationResult
    risk_assessment: RiskAssessment
    output_at: datetime

    # NEW: Optional evidence fields (absent when retrieval is not run)
    evidence_candidates: list[EvidenceCandidate] = Field(default_factory=list)
    retrieval_trace: RetrievalTrace | None = None
```

**Rationale for extending rather than subclassing:**
- Avoids a breaking change to the existing TicketOutput schema -- callers that do not care about evidence ignore the new fields.
- evidence_candidates defaults to an empty list so code iterating over candidates does not need None checks.
- retrieval_trace is None when retrieval is not run (e.g., when only stages 1-3 execute); it holds a RetrievalTrace on success or partial-failure.
- A subclass like TicketOutputWithEvidence would require all downstream code to know which type they have, creating a proliferation of isinstance() checks.

### New: EvidenceCandidate

```python
class EvidenceCandidate(BaseModel):
    """Minimal evidence item extracted from a fused retrieval result."""

    chunk_id: UUID
    doc_id: UUID
    doc_type: DocType
    source_id: UUID   # FK to source table row (knowledge_faq.id, etc.)
    source_table: str  # "knowledge_faq", "knowledge_policy", or "knowledge_case"
    content: str
    score: float  # RRF score from fusion
    rank: int     # Rank in fused results (1-indexed)
```

**Why not reuse FusedResult directly:**
- FusedResult carries retrieval-internal fields (keyword_rank, vector_rank, keyword_contribution, vector_contribution, sources) that are useful for debugging but not needed by downstream consumers (future reply generation, UI rendering).
- EvidenceCandidate includes source_table which is NOT on FusedResult -- the source table (e.g., "knowledge_faq") is needed to know which source document to fetch for full context.
- A wrapper with only the fields needed for downstream use keeps the API surface minimal and focused.

**Deriving source_table from doc_type:**

| doc_type | source_table |
|----------|-------------|
| DocType.FAQ | "knowledge_faq" |
| DocType.POLICY | "knowledge_policy" |
| DocType.CASE | "knowledge_case" |

The source table name can also be obtained by joining knowledge_chunks.source_table from the database, but since DocType and source_table have a 1:1 mapping at the chunk level, the mapping is deterministic and can be done in application code without an extra DB round-trip.

## Evidence Candidate Schema

### Full EvidenceCandidate definition:

| Field | Type | Description |
|-------|------|-------------|
| chunk_id | UUID | Primary key of the knowledge_chunks row |
| doc_id | UUID | Foreign key to the source document (FAQ, Policy, or Case) |
| doc_type | DocType | Enum: FAQ, POLICY, or CASE |
| source_id | UUID | Primary key of the source table row (knowledge_faq.id, etc.) |
| source_table | str | Source table name: "knowledge_faq", "knowledge_policy", or "knowledge_case" |
| content | str | The chunk's text content (the matched passage) |
| score | float | RRF fusion score (higher is better) |
| rank | int | 1-indexed rank in the fused results list |

### Extraction logic (extract_evidence_candidates):

```python
def extract_evidence_candidates(
    fused_results: list[FusedResult],
    min_score: float = 0.0,
) -> list[EvidenceCandidate]:
    candidates = []
    for i, fused in enumerate(fused_results):
        if fused.rrf_score < min_score:
            continue
        candidates.append(EvidenceCandidate(
            chunk_id=fused.chunk_id,
            doc_id=fused.doc_id,
            doc_type=fused.doc_type,
            source_id=fused.doc_id,  # doc_id IS the source table PK in current seed data
            source_table=_doc_type_to_source_table(fused.doc_type),
            content=fused.content,
            score=fused.rrf_score,
            rank=i + 1,
        ))
    return candidates
```

### Score threshold behavior:
- Default min_score=0.0 means all fused results pass.
- When ALL results fall below threshold: evidence_candidates is empty, INSUFFICIENT_EVIDENCE is added to risk flags.
- The threshold is intentionally low (0.0) for the MVP because RRF scores have no absolute meaning -- they are relative within a single query execution. A data-driven threshold can be set once we have evaluation metrics.

## Pipeline Changes

### Current intake_risk_pipeline() structure:

```python
def intake_risk_pipeline(raw_ticket: RawTicket) -> TicketOutput:
    # Stage 1 (try/except)
    # Stage 2 (try/except)
    # Stage 3 (try/except)
    return TicketOutput(...)
```

### New intake_risk_pipeline() structure:

```python
def intake_risk_pipeline(
    raw_ticket: RawTicket,
    enable_retrieval: bool = True,
) -> TicketOutput:
    # Stage 1 (try/except) -- unchanged
    # Stage 2 (try/except) -- unchanged
    # Stage 3 (try/except) -- unchanged

    # NEW: Stage 4 (try/except)
    if enable_retrieval:
        try:
            query = build_retrieval_query(
                normalized_text=normalized_ticket.text,
                intent=classification.intent,
                risk_flags=risk_assessment.flags,
            )
            if not query.strip():
                # Empty query: skip retrieval
                evidence_candidates = []
                trace = None
                risk_assessment.flags.add(RiskFlag.INSUFFICIENT_EVIDENCE)
                risk_assessment.must_human_review = True
            else:
                doc_types = map_intent_to_doc_types(classification.intent)
                trace = hybrid_retrieval(
                    query=query,
                    top_k=10,
                    doc_types=doc_types,
                )
                evidence_candidates = extract_evidence_candidates(
                    trace.fused_results,
                    min_score=0.0,
                )
                if not evidence_candidates:
                    risk_assessment.flags.add(RiskFlag.INSUFFICIENT_EVIDENCE)
                    risk_assessment.must_human_review = True
        except Exception:
            # Retrieval failure = flag for human review + empty evidence
            risk_assessment.flags.add(RiskFlag.INSUFFICIENT_EVIDENCE)
            risk_assessment.must_human_review = True
            evidence_candidates = []
            trace = RetrievalTrace(
                query="",
                query_embedding=[],
                total_latency_ms=0,
            )
    else:
        evidence_candidates = []
        trace = None

    return TicketOutput(
        ticket_id=str(uuid.uuid4()),
        raw_ticket=raw_ticket,
        normalized_ticket=normalized_ticket,
        classification=classification,
        risk_assessment=risk_assessment,
        output_at=datetime.utcnow(),
        evidence_candidates=evidence_candidates,
        retrieval_trace=trace,
    )
```

### Key design decisions in the pipeline:

1. **enable_retrieval flag**: Allows running just stages 1-3 without retrieval (backward compatible). Defaults to True so the full pipeline runs by default.

2. **Risk flags are mutable**: risk_assessment.flags is a set -- adding INSUFFICIENT_EVIDENCE in place avoids creating a new RiskAssessment object and preserves the original assessment's integrity. must_human_review is set to True explicitly on no-evidence or failure.

3. **Trace on failure**: A minimal RetrievalTrace with empty fields is still returned (not None) so callers can check trace.total_latency_ms == 0 or trace.query == "" to detect failure, rather than deal with None checks.

4. **Stage 4 runs AFTER risk assessment**: This is intentional. The risk assessment may already have set INSUFFICIENT_EVIDENCE from the ticket text analysis (e.g., text shorter than 10 chars with no order number). Retrieval adds another source of INSUFFICIENT_EVIDENCE -- now from the knowledge base side.

5. **Empty query skip**: If build_retrieval_query returns an empty or whitespace-only string (happens when text is empty and intent is OTHER), retrieval is skipped entirely and trace is set to None.

## Graceful Degradation

### Failure modes and responses:

| Failure Mode | Trigger | Response |
|-------------|---------|----------|
| Intake failure | Exception in intake_pipeline() | Empty normalized_ticket.text; query built from intent label only; retrieval may still work |
| Classification failure | Exception in IntentClassifier | Intent = OTHER; no doc_type filter applied; wide recall |
| Risk assessment failure | Exception in RiskAssessor | Default risk with LOW_CONFIDENCE flag; Stage 4 proceeds |
| Empty query | Text is empty AND intent is OTHER | Skip retrieval entirely; evidence_candidates=[]; INSUFFICIENT_EVIDENCE flag; trace=None |
| Retrieval exception | DB connection error, timeout, etc. | INSUFFICIENT_EVIDENCE flag; evidence_candidates=[]; minimal RetrievalTrace; must_human_review=True |
| No fused results | RRF returned zero results | INSUFFICIENT_EVIDENCE flag; evidence_candidates=[]; full RetrievalTrace preserved; must_human_review=True |
| All scores below threshold | All RRF scores < min_score | INSUFFICIENT_EVIDENCE flag; evidence_candidates=[]; full RetrievalTrace preserved; must_human_review=True |

### Invariants preserved on failure:

1. evidence_candidates is always a list (never None).
2. retrieval_trace is either a valid RetrievalTrace (success or degraded) or None (retrieval disabled or skipped).
3. must_human_review is always True when retrieval fails or returns nothing.
4. The INSUFFICIENT_EVIDENCE flag is added to the existing risk_assessment.flags set -- it does not overwrite other flags.
5. Exceptions in Stage 4 do NOT prevent TicketOutput from being assembled -- the pipeline always returns a result.

## Intent-to-DocType Mapping

### Mapping table:

| IntentClass | DocTypes to search | Rationale |
|-------------|-------------------|-----------|
| REFUND | FAQ, POLICY, CASE | Refund touches all three: FAQ for procedure, POLICY for eligibility, CASE for precedent |
| RETURN_EXCHANGE | FAQ, POLICY, CASE | Similar to refund -- FAQ for process, POLICY for terms, CASE for similar situations |
| ACCOUNT_ISSUE | FAQ, POLICY | Account issues are mostly FAQ (password reset, login) and POLICY (account security, data handling); historical CASE may be irrelevant or privacy-sensitive |
| TECHNICAL_ISSUE | FAQ | Technical bugs are covered by FAQ (troubleshooting); rarely by POLICY or CASE |
| PRODUCT_CONSULTING | FAQ | Product questions answered by FAQ (specs, usage); CASE and POLICY are irrelevant |
| LOGISTICS | FAQ, POLICY | Logistics questions: FAQ for tracking/process, POLICY for shipping terms |
| COMPLAINT | FAQ, POLICY, CASE | Complaints need broad recall: FAQ for escalation process, POLICY for rights, CASE for similar resolutions |
| OTHER | None (no filter) | Unknown intent: search ALL doc types for maximum recall |

### Implementation:

```python
INTENT_TO_DOC_TYPES: dict[IntentClass, list[DocType] | None] = {
    IntentClass.REFUND: [DocType.FAQ, DocType.POLICY, DocType.CASE],
    IntentClass.RETURN_EXCHANGE: [DocType.FAQ, DocType.POLICY, DocType.CASE],
    IntentClass.ACCOUNT_ISSUE: [DocType.FAQ, DocType.POLICY],
    IntentClass.TECHNICAL_ISSUE: [DocType.FAQ],
    IntentClass.PRODUCT_CONSULTING: [DocType.FAQ],
    IntentClass.LOGISTICS: [DocType.FAQ, DocType.POLICY],
    IntentClass.COMPLAINT: [DocType.FAQ, DocType.POLICY, DocType.CASE],
    IntentClass.OTHER: None,  # None = no filter = all doc types
}

def map_intent_to_doc_types(intent: IntentClass) -> list[DocType] | None:
    return INTENT_TO_DOC_TYPES.get(intent)  # None for OTHER
```

- None is passed through to hybrid_retrieval(doc_types=None), which means "no filter, search all".
- Explicitly selecting [DocType.FAQ, DocType.POLICY, DocType.CASE] is equivalent to None for the initial dataset but becomes important when new document types are added.
- The ACCOUNT_ISSUE exclusion of CASE documents is the most opinionated choice -- account-related cases may reference customer PII and are excluded from retrieval by default.

### Trade-offs:

- **Over-filtering risk**: If the intent classifier is wrong (e.g., classifies a refund as ACCOUNT_ISSUE), the retrieval will miss relevant FAQ/POLICY/CASE content. Mitigation: INSUFFICIENT_EVIDENCE flag triggers human review, which can re-classify.
- **Under-filtering risk**: Searching all doc types for OTHER may return noise. Mitigation: RRF scoring naturally ranks relevant content higher; low-scoring results are below threshold and filtered out by extract_evidence_candidates.

## Module Boundaries

### What goes WHERE:

| Component | Location | Justification |
|-----------|----------|---------------|
| build_retrieval_query() | src/ticketpilot/retrieval/query_builder.py | Lives in the retrieval module because it contains intent-to-Chinese-business-term mapping for 8 intents, risk-flag-to-Chinese-business-term mapping for 5 flags, text concatenation, and deduplication logic. Keeping this out of pipeline.py prevents pipeline.py from becoming a god object and makes query construction independently testable. |
| map_intent_to_doc_types() | src/ticketpilot/pipeline.py | Simple dictionary lookup; co-locates with pipeline. |
| extract_evidence_candidates() | src/ticketpilot/retrieval/evidence_mapper.py | Already implemented as map_fused_to_evidence() in evidence_mapper.py. |
| EvidenceCandidate schema | src/ticketpilot/schema/evidence.py | Lives alongside TicketOutput since it is a field on TicketOutput. |
| TicketOutput extension | src/ticketpilot/schema/ticket.py | Same file as current definition. |
| hybrid_retrieval() | src/ticketpilot/retrieval/pipeline.py | **UNCHANGED**. Imported and called from main pipeline. |
| FusedResult, RetrievalTrace | src/ticketpilot/retrieval/traces.py | **UNCHANGED**. Imported for type annotations and evidence extraction. |
| DocType | src/ticketpilot/retrieval/schema/knowledge.py | **UNCHANGED**. Imported for intent mapping. |

### What stays UNCHANGED:

- src/ticketpilot/retrieval/ -- entire module. It is a stable, independently tested retrieval system. The pipeline calls hybrid_retrieval() with the same arguments it already supports.
- src/ticketpilot/classification/ -- unchanged.
- src/ticketpilot/risk/ -- unchanged (except that RiskFlag.INSUFFICIENT_EVIDENCE may be set by the pipeline after retrieval, but the assessor itself is unchanged).
- src/ticketpilot/intake/ -- unchanged.
- db/migrations/ -- unchanged (no new tables or indices needed).
- data/knowledge/ -- unchanged (existing seed data used as-is).

### Why query_builder lives in retrieval/ rather than pipeline.py:

1. The query construction logic includes intent-to-Chinese-business-term mapping for 8 intents, risk-flag-to-Chinese-business-term mapping for 5 flags, text concatenation, and deduplication. This exceeds 30 lines immediately.
2. Keeping the query builder in src/ticketpilot/retrieval/query_builder.py prevents pipeline.py from becoming a god object — pipeline.py focuses on orchestration, while the retrieval module owns query construction.
3. Query construction is retrieval logic (it builds the input to hybrid_retrieval()), not pipeline orchestration logic. It belongs alongside keyword_search.py and vector_search.py in the retrieval module.
4. Independent testability: query_builder can be unit-tested without mocking the pipeline, and the pipeline can be tested with a mock query_builder.

## Risks / Trade-offs

**Risk: Simple query concatenation may produce suboptimal retrieval.**
- The current approach appends the Chinese intent label to the ticket text. If the ticket text already contains the label keyword (e.g., "退款" appears in both text and label), the duplication may bias keyword search toward that term.
- **Mitigation**: RRF fusion balances keyword and vector signals. Vector search captures semantic similarity regardless of exact term duplication. Evaluate retrieval quality with the golden cases already defined in the retrieval module (6 cases for smoke testing).

**Risk: Intent classifier errors cascade into doc_type filtering errors.**
- If IntentClass.ACCOUNT_ISSUE is predicted but the ticket is truly a refund, CASE documents (which contain historical refund resolutions) will be excluded.
- **Mitigation**: When no evidence is found, INSUFFICIENT_EVIDENCE triggers human review. The human reviewer can override the intent classification. In a future iteration, fallback to broad retrieval (no filter) when the initial filtered search returns empty.

**Risk: must_human_review mutation after risk assessment may surprise callers.**
- The risk assessor may set must_human_review=False, but the pipeline later sets it to True after a retrieval failure.
- **Mitigation**: This is documented behavior. Callers should always read TicketOutput.risk_assessment.must_human_review as the final authoritative flag, not an intermediate assessment value.

**Risk: In-memory RetrievalTrace is not persisted.**
- The trace is returned in the TicketOutput object but not written to the retrieval_traces database table. If the pipeline output is not explicitly saved, traces are lost.
- **Mitigation**: Trace persistence is explicitly a non-goal for this change. A follow-up change can add save_trace_to_db() to the pipeline. The current design leaves the trace in-memory so that integration tests can assert on it without database dependencies.

**Risk: RetrievalTrace from the retrieval module carries 1536-dimensional embeddings in-memory.**
- The trace includes query_embedding: list[float] (1536 floats). For high-throughput pipelines, this adds memory pressure.
- **Mitigation**: For the MVP throughput (single tickets, not batch), this is negligible. If batch processing is needed, the query embedding can be excluded from the trace or truncated.

**Trade-off: EvidenceCandidate vs. reusing FusedResult.**
- Creating a new EvidenceCandidate schema adds one more Pydantic model to the codebase. However, FusedResult exposes retrieval-internal fields (keyword_rank, vector_rank, keyword_contribution, vector_contribution, sources) that are not relevant to downstream consumers and would leak the retrieval module's internal representation.
- The source_table field on EvidenceCandidate is not on FusedResult and is needed for source document lookup. Adding it to FusedResult would couple the retrieval schema to pipeline concerns.
- Decision: EvidenceCandidate is the right boundary.

## Open Questions

1. **Score threshold calibration**: What is the right min_score for extract_evidence_candidates? RRF scores are bounded between 0 and approximately 2/(k+1) = 2/61 = 0.0328. Scores below ~0.015 typically indicate documents ranked very low by both rankers. Should the threshold be an absolute RRF score, a relative percentile, or a fixed top-k cutoff? Answer: Use top-k=10 with no score threshold for the MVP; add score-based filtering after evaluation data is collected.

2. **Should the query include the ticket's extracted entities (order_numbers, product_info)?**
   The NormalizedTicket has order_numbers, product_info, and amount. Including these in the query (e.g., "订单号 RK20240315 耳机 质量问题 退款") might improve keyword recall. However, these fields are structurally different from the text and may not be in the knowledge base chunks. Decision: Defer to a follow-up; start with text + intent label only.

3. **Should COMPLAINT intents search CASE documents?**
   Historical complaint cases could provide resolution precedent but may contain sensitive customer information. The current seed data (12 cases) does not have PII, but production case data would. Decision: Include CASE for complaints in the mapping but flag for human review on all complaint intents regardless.

4. **What is the recovery path when retrieval returns evidence but risk assessment already flagged INSUFFICIENT_EVIDENCE?**
   The risk assessor sets INSUFFICIENT_EVIDENCE based on ticket metadata (no order number, vague description). Retrieval may find relevant documents despite this. Should retrieval success clear the flag? Decision: No -- INSUFFICIENT_EVIDENCE set by the risk assessor relates to ticket-level evidence, not knowledge-base evidence. Both flags can coexist. A future reconciliation stage could resolve this.

5. **Should retrieval results be cached per query?**
   Identical queries from different tickets may produce identical retrieval results. Caching would reduce latency and database load. Decision: Not for the MVP. Add caching when throughput requirements are defined.

6. **Does the RetrievalTrace field on TicketOutput create a circular import?**
   schema/ticket.py would need to import RetrievalTrace from retrieval/traces.py. This is a one-way dependency (schema depends on retrieval), which is fine because retrieval already depends on nothing from the ticket schema. No circular dependency. Confirm during implementation.
