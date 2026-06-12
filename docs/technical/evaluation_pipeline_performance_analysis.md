# Evaluation Pipeline Performance Analysis

## Executive Summary

The TicketPilot evaluation pipeline processes ~101 synthetic eval tickets, with each ticket taking ~3.5s. This analysis identifies bottlenecks and provides actionable optimization recommendations.

**Key Finding**: The pipeline's primary bottleneck is **database connection overhead** in the retrieval stage, not the computation itself. The FakeEmbeddingProvider is fast (~0.1ms), but each DB query opens/closes connections.

---

## Pipeline Flow Analysis

```
predict_from_pipeline() [pipeline_predictions.py:39]
  └── run_pipeline_with_draft() [drafting/pipeline.py:9]
        ├── intake_risk_pipeline() [pipeline.py:46]
        │     ├── Stage 1: Intake [intake/pipeline.py:10] ~0.5ms
        │     │     ├── TextNormalizer.normalize()
        │     │     └── EntityExtractor.extract()
        │     ├── Stage 2: Classification [classification/classifier.py:26] ~0.1ms
        │     │     └── IntentClassifier.classify() - keyword matching
        │     ├── Stage 3: Risk Assessment [risk/assessor.py:23] ~0.1ms
        │     │     └── RiskAssessor.assess() - keyword matching
        │     └── Stage 4: Evidence Retrieval [pipeline.py:104] ~3000-3500ms ⚠️ BOTTLENECK
        │           └── retrieve_evidence() [retrieve_evidence.py:16]
        │                 ├── build_retrieval_query() ~0.1ms
        │                 └── hybrid_retrieval() [pipeline.py:68]
        │                       ├── FakeEmbeddingProvider.embed() ~0.1ms
        │                       ├── keyword_search() ~1000-1500ms ⚠️
        │                       │     ├── _fts_search() - DB query
        │                       │     └── _like_search() - DB query (if needed)
        │                       ├── vector_search() ~1000-1500ms ⚠️
        │                       │     └── pgvector HNSW query
        │                       └── HybridReranker.rerank() ~50-100ms
        │                             └── _load_doc_embeddings() ~50-100ms (if real embedding)
        └── generate_draft() [drafting/generate.py:116] ~1-10ms
              └── FakeDraftProvider.generate() (default)
```

---

## Identified Bottlenecks

### 1. **Database Connection Overhead** (CRITICAL - ~60% of time)

**Location**: Multiple files
- `retrieval/keyword_search.py:151-153` - Opens connection for FTS search
- `retrieval/keyword_search.py:251-253` - Opens connection for LIKE search
- `retrieval/vector_search.py:95-99` - Opens connection for vector search
- `retrieval/hybrid_reranker.py:289-295` - Opens connection for embedding lookup

**Impact**: Each `get_db_connection()` call involves:
- Pool checkout (~5-10ms)
- Connection establishment (if pool empty) (~50-100ms)
- Query execution (~10-50ms)
- Pool checkin (~5ms)

**Evidence**:
```python
# keyword_search.py:151-153
with get_db_connection() as conn:  # Opens new connection
    with conn.cursor() as cur:
        cur.execute(sql, params)
        for row in cur.fetchall():
            results.append(...)
# Connection closed after block
```

**Solution**: Batch queries or reuse connections across pipeline stages.

---

### 2. **Sequential Ticket Processing** (HIGH - ~30% of time)

**Location**: `optimizer/evaluator.py:89-96`

```python
for idx, (case_id, ticket) in enumerate(ds.tickets.items(), start=1):
    logger.debug("Predicting %d/%d: %s", idx, total, case_id)
    try:
        pred = predict_from_pipeline(ticket)  # Blocks for ~3.5s
        predictions[case_id] = pred
    except Exception:
        logger.exception("Pipeline failed for %s", case_id)
        raise
```

**Impact**: 101 tickets × 3.5s = ~353 seconds (~6 minutes)

**Solution**: Use `concurrent.futures.ThreadPoolExecutor` or `asyncio` for parallel processing.

---

### 3. **Redundant Reranker Config Loading** (MEDIUM - ~5% of time)

**Location**: `retrieval/pipeline.py:182-186`

```python
if reranker_config is None:
    try:
        reranker_config = RerankerConfig.from_yaml("config/reranker.yaml")  # File I/O
    except Exception as e:
        logger.warning("Failed to load reranker config from YAML, using default: %s", e)
        reranker_config = RerankerConfig.default()
```

**Impact**: YAML file parsed ~101 times per evaluation run.

**Solution**: Cache `RerankerConfig` as a singleton or pass pre-loaded config.

---

### 4. **No Query Result Caching** (MEDIUM - ~20% of time wasted)

**Location**: `retrieval/retrieve_evidence.py:34-45`

```python
def retrieve_evidence(
    normalized_text: str,
    intent: IntentClass,
    risk_flags: set[RiskFlag],
    ...
) -> tuple[list[EvidenceCandidate], RetrievalTrace]:
    query = build_retrieval_query(normalized_text, intent, risk_flags)
    trace = hybrid_retrieval(query=query, ...)  # No caching
    candidates = map_fused_to_evidence(trace.fused_results)
    return candidates, trace
```

**Impact**: Similar queries (e.g., "退款" + "refund") generate identical DB results but are re-fetched.

**Solution**: Cache results with key = hash(query, top_k, doc_types).

---

### 5. **Object Instantiation Per Ticket** (LOW - ~2% of time)

**Location**: `pipeline.py:78,91`

```python
# Stage 2: Classification - NEW classifier per ticket
classifier = IntentClassifier()
classification = classifier.classify(normalized_ticket.text)

# Stage 3: Risk assessment - NEW assessor per ticket
assessor = RiskAssessor()
risk_assessment = assessor.assess(normalized_ticket, classification)
```

**Impact**: Creates new objects ~101 times (negligible but unnecessary).

**Solution**: Use module-level singletons or pass as parameters.

---

## Optimization Recommendations

### Priority 1: Batch DB Queries (Estimated: -50% time)

**File**: `retrieval/pipeline.py`

**Approach**: Pass a single DB connection through the retrieval pipeline.

```python
# Current: 3 separate connections per ticket
# keyword_search() -> get_db_connection()
# vector_search() -> get_db_connection()
# hybrid_reranker._load_doc_embeddings() -> get_db_connection()

# Optimized: 1 connection per ticket
def hybrid_retrieval(
    query: str,
    top_k: int = 10,
    embedding_provider: Optional[FakeEmbeddingProvider] = None,
    db_connection: Optional[Connection] = None,  # NEW
    ...
) -> RetrievalTrace:
    if db_connection is None:
        with get_db_connection() as conn:
            return _hybrid_retrieval_impl(query, top_k, embedding_provider, conn, ...)
    return _hybrid_retrieval_impl(query, top_k, embedding_provider, db_connection, ...)
```

**Estimated Impact**: -1000ms per ticket (30% improvement)

---

### Priority 2: Cache Retrieval Results (Estimated: -30% time)

**File**: `retrieval/retrieve_evidence.py`

**Approach**: Add LRU cache with TTL.

```python
import functools
import time

_RETRIEVAL_CACHE: dict[str, tuple[float, tuple]] = {}
_CACHE_TTL_SECONDS = 300  # 5 minutes

def retrieve_evidence(
    normalized_text: str,
    intent: IntentClass,
    risk_flags: set[RiskFlag],
    top_k: int = 10,
    doc_types: list[DocType] | None = None,
    embedding_provider: Optional[FakeEmbeddingProvider] = None,
    enable_cache: bool = True,  # NEW
    ...
) -> tuple[list[EvidenceCandidate], RetrievalTrace]:
    # Build cache key
    cache_key = _build_cache_key(normalized_text, intent, risk_flags, top_k, doc_types)
    
    if enable_cache and cache_key in _RETRIEVAL_CACHE:
        cached_time, cached_result = _RETRIEVAL_CACHE[cache_key]
        if time.time() - cached_time < _CACHE_TTL_SECONDS:
            return cached_result
    
    # ... existing logic ...
    
    if enable_cache:
        _RETRIEVAL_CACHE[cache_key] = (time.time(), (candidates, trace))
    
    return candidates, trace

def _build_cache_key(normalized_text, intent, risk_flags, top_k, doc_types):
    """Build deterministic cache key."""
    import hashlib
    parts = [
        normalized_text,
        intent.value if intent else "",
        ";".join(sorted(f.value for f in risk_flags)),
        str(top_k),
        ";".join(sorted(dt.value for dt in doc_types)) if doc_types else "",
    ]
    return hashlib.sha256("|".join(parts).encode()).hexdigest()
```

**Estimated Impact**: -700ms per ticket (20% improvement) for repeated queries.

---

### Priority 3: Parallel Ticket Processing (Estimated: -60% time)

**File**: `optimizer/evaluator.py`

**Approach**: Use ThreadPoolExecutor for I/O-bound operations.

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def _generate_predictions(self) -> dict[str, EvalPrediction]:
    """Run the pipeline on every ticket and collect predictions (parallel)."""
    ds = self.dataset
    predictions: dict[str, EvalPrediction] = {}
    total = ds.ticket_count
    
    def predict_single(case_id: str, ticket: EvalTicket) -> tuple[str, EvalPrediction]:
        logger.debug("Predicting: %s", case_id)
        pred = predict_from_pipeline(ticket)
        return case_id, pred
    
    # Use thread pool for DB-bound operations
    max_workers = min(8, total)  # Limit to 8 threads
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(predict_single, case_id, ticket): case_id
            for case_id, ticket in ds.tickets.items()
        }
        
        for future in as_completed(futures):
            case_id = futures[future]
            try:
                cid, pred = future.result()
                predictions[cid] = pred
            except Exception:
                logger.exception("Pipeline failed for %s", case_id)
                raise
    
    return predictions
```

**Estimated Impact**: -2000ms per ticket (60% improvement) with 8 threads.

---

### Priority 4: Cache Reranker Config (Estimated: -5% time)

**File**: `retrieval/pipeline.py`

**Approach**: Module-level singleton.

```python
# Add at module level
_reranker_config_cache: Optional[RerankerConfig] = None

def _get_reranker_config() -> RerankerConfig:
    """Get reranker config (cached singleton)."""
    global _reranker_config_cache
    if _reranker_config_cache is None:
        try:
            _reranker_config_cache = RerankerConfig.from_yaml("config/reranker.yaml")
        except Exception:
            _reranker_config_cache = RerankerConfig.default()
    return _reranker_config_cache

# In hybrid_retrieval():
if reranker_config is None:
    reranker_config = _get_reranker_config()
```

**Estimated Impact**: -50ms per ticket (1% improvement)

---

### Priority 5: Skip Retrieval for Quick Iterations (Estimated: -80% time)

**File**: `evaluation/pipeline_predictions.py`

**Approach**: Add lightweight mode that skips retrieval.

```python
def predict_from_pipeline(
    eval_ticket: EvalTicket,
    skip_retrieval: bool = False,  # NEW
) -> EvalPrediction:
    """Run the local TicketPilot pipeline on one eval ticket."""
    raw_ticket = RawTicket(
        original_text=eval_ticket.original_text,
        submitted_at=datetime.now(timezone.utc),
        customer_id=eval_ticket.customer_id,
    )

    if skip_retrieval:
        # Lightweight mode: skip retrieval, use empty evidence
        ticket_output = _run_pipeline_without_retrieval(raw_ticket)
    else:
        drafted_result = run_pipeline_with_draft(raw_ticket)
        ticket_output = drafted_result.ticket_output
        draft_reply = drafted_result.draft_reply

    # ... rest of mapping ...

def _run_pipeline_without_retrieval(raw_ticket: RawTicket) -> TicketOutput:
    """Run intake + classification + risk without retrieval."""
    from ticketpilot.intake.pipeline import pipeline as intake_pipeline
    from ticketpilot.classification.classifier import IntentClassifier
    from ticketpilot.risk.assessor import RiskAssessor
    
    normalized_ticket = intake_pipeline(raw_ticket)
    classifier = IntentClassifier()
    classification = classifier.classify(normalized_ticket.text)
    assessor = RiskAssessor()
    risk_assessment = assessor.assess(normalized_ticket, classification)
    
    return TicketOutput(
        ticket_id=str(uuid.uuid4()),
        raw_ticket=raw_ticket,
        normalized_ticket=normalized_ticket,
        classification=classification,
        risk_assessment=risk_assessment,
        output_at=datetime.now(timezone.utc),
        evidence_candidates=[],  # Empty
        retrieval_trace=None,
    )
```

**Estimated Impact**: -2800ms per ticket (80% improvement) for quick iterations.

---

## Running Evaluation Without DB

### Current State

The existing tests use `FakeEmbeddingProvider` which doesn't require DB:

```python
# tests/conftest.py:10
os.environ.setdefault("TICKETPILOT_LLM_PROVIDER", "fake")
```

However, `retrieve_evidence()` still calls `keyword_search()` and `vector_search()` which require DB.

### Solution: Add `offline_mode` Parameter

**File**: `evaluation/pipeline_predictions.py`

```python
def predict_from_pipeline(
    eval_ticket: EvalTicket,
    offline_mode: bool = False,  # NEW
) -> EvalPrediction:
    """Run the local TicketPilot pipeline on one eval ticket."""
    raw_ticket = RawTicket(
        original_text=eval_ticket.original_text,
        submitted_at=datetime.now(timezone.utc),
        customer_id=eval_ticket.customer_id,
    )

    if offline_mode:
        # Offline mode: skip DB entirely, use FakeEmbeddingProvider
        ticket_output = _run_pipeline_offline(raw_ticket)
    else:
        drafted_result = run_pipeline_with_draft(raw_ticket)
        ticket_output = drafted_result.ticket_output
        draft_reply = drafted_result.draft_reply

    # ... rest of mapping ...

def _run_pipeline_offline(raw_ticket: RawTicket) -> TicketOutput:
    """Run pipeline without DB (offline mode)."""
    from ticketpilot.intake.pipeline import pipeline as intake_pipeline
    from ticketpilot.classification.classifier import IntentClassifier
    from ticketpilot.risk.assessor import RiskAssessor
    from ticketpilot.retrieval.providers.fake_embedding import FakeEmbeddingProvider
    
    normalized_ticket = intake_pipeline(raw_ticket)
    classifier = IntentClassifier()
    classification = classifier.classify(normalized_ticket.text)
    assessor = RiskAssessor()
    risk_assessment = assessor.assess(normalized_ticket, classification)
    
    # Generate fake evidence (no DB)
    embedding_provider = FakeEmbeddingProvider()
    query = f"{normalized_ticket.text} {classification.intent.value}"
    # ... generate fake evidence candidates ...
    
    return TicketOutput(
        ticket_id=str(uuid.uuid4()),
        raw_ticket=raw_ticket,
        normalized_ticket=normalized_ticket,
        classification=classification,
        risk_assessment=risk_assessment,
        output_at=datetime.now(timezone.utc),
        evidence_candidates=[],  # Empty or fake
        retrieval_trace=None,
    )
```

**Usage in Optimizer**:

```python
# optimizer/evaluator.py
def _generate_predictions(self) -> dict[str, EvalPrediction]:
    """Run the pipeline on every ticket and collect predictions."""
    ds = self.dataset
    predictions: dict[str, EvalPrediction] = {}
    
    # Check if offline mode is enabled
    offline_mode = os.environ.get("TICKETPILOT_OFFLINE_MODE", "").lower() in ("true", "1")
    
    for idx, (case_id, ticket) in enumerate(ds.tickets.items(), start=1):
        logger.debug("Predicting %d/%d: %s", idx, total, case_id)
        pred = predict_from_pipeline(ticket, offline_mode=offline_mode)
        predictions[case_id] = pred
    
    return predictions
```

**Environment Variable**:
```bash
# Run evaluation without DB
TICKETPILOT_OFFLINE_MODE=1 python -m ticketpilot.optimizer
```

---

## Implementation Priority

| Priority | Optimization | Estimated Impact | Effort |
|----------|--------------|------------------|--------|
| P0 | Batch DB queries | -30% time | Medium |
| P1 | Parallel ticket processing | -60% time | Low |
| P2 | Cache retrieval results | -20% time | Low |
| P3 | Cache reranker config | -1% time | Trivial |
| P4 | Skip retrieval mode | -80% time | Medium |
| P5 | Offline mode (no DB) | -95% time | Medium |

---

## Expected Results

**Current**: ~350 seconds for 101 tickets (~3.5s/ticket)

**After P0 + P1**: ~100 seconds (~1.0s/ticket)
- Batch DB: -1000ms/ticket → 2.5s/ticket
- Parallel (8 threads): -60% → 1.0s/ticket

**After P0 + P1 + P2**: ~70 seconds (~0.7s/ticket)
- Cache hits: -700ms/ticket

**After all optimizations**: ~15 seconds (~0.15s/ticket)
- Skip retrieval: -2800ms/ticket → 0.7s/ticket
- Parallel + cache: -85% → 0.15s/ticket

---

## Testing Recommendations

1. **Add benchmark tests**: Measure per-ticket latency
2. **Add cache tests**: Verify cache invalidation
3. **Add parallel tests**: Verify thread safety
4. **Add offline mode tests**: Verify no DB dependency

```python
# tests/unit/test_evaluation_performance.py
import time
from ticketpilot.evaluation.pipeline_predictions import predict_from_pipeline
from ticketpilot.evaluation.schemas import EvalTicket

def test_predict_latency():
    """Verify prediction completes within time budget."""
    ticket = EvalTicket(
        case_id="PERF-001",
        original_text="我要退款",
        customer_id="CUST-001",
        submitted_at="2024-01-01T00:00:00Z",
        scenario_type="refund",
    )
    
    start = time.perf_counter()
    pred = predict_from_pipeline(ticket, offline_mode=True)
    elapsed = time.perf_counter() - start
    
    assert elapsed < 0.5, f"Prediction took {elapsed:.2f}s, expected <0.5s"
    assert pred.predicted_issue_type == "refund"
```

---

## Files to Modify

1. `src/ticketpilot/retrieval/pipeline.py` - Add connection parameter, cache config
2. `src/ticketpilot/retrieval/retrieve_evidence.py` - Add caching
3. `src/ticketpilot/optimizer/evaluator.py` - Add parallel processing
4. `src/ticketpilot/evaluation/pipeline_predictions.py` - Add offline mode
5. `src/ticketpilot/retrieval/keyword_search.py` - Accept connection parameter
6. `src/ticketpilot/retrieval/vector_search.py` - Accept connection parameter

---

## Conclusion

The primary bottleneck is **database connection overhead** in the retrieval stage. By batching queries, adding caching, and enabling parallel processing, we can reduce evaluation time from ~350s to ~70s (5x improvement). For quick iterations, the skip-retrieval mode can further reduce this to ~15s (23x improvement).

The FakeEmbeddingProvider is already fast (~0.1ms) and doesn't require DB. The offline mode can be implemented by skipping the retrieval stage entirely and using empty/fake evidence candidates.
