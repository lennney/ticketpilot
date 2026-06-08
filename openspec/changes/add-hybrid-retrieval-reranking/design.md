# Design: Hybrid Retrieval Reranking

## Architecture Overview

```
                    ┌─────────────────────────────────────┐
                    │         MultiQueryExpander           │
                    │  (LLM 生成 2 个查询变体 + 原始查询)    │
                    └──────────────┬──────────────────────┘
                                   │ 3 queries
                    ┌──────────────▼──────────────────────┐
                    │     Parallel Retrieval (3 路)        │
                    │  keyword_search + vector_search      │
                    │  per query → RRF fusion              │
                    └──────────────┬──────────────────────┘
                                   │ 3 × top_2k fused results
                    ┌──────────────▼──────────────────────┐
                    │        Result Merger + Dedup         │
                    │  (chunk_id 去重, 取最高 RRF score)    │
                    └──────────────┬──────────────────────┘
                                   │ merged candidates
                    ┌──────────────▼──────────────────────┐
                    │         HybridReranker               │
                    │                                      │
                    │  signal_1: rrf_score          (w1)   │
                    │  signal_2: embedding_sim      (w2)   │
                    │  signal_3: intent_meta_boost  (w3)   │
                    │  signal_4: content_quality    (w4)   │
                    │                                      │
                    │  final_score = Σ(wi × normalized_i)  │
                    └──────────────┬──────────────────────┘
                                   │ reranked top_k
                    ┌──────────────▼──────────────────────┐
                    │         RetrievalTrace               │
                    │  (所有信号 + 权重 + 最终分数)          │
                    └─────────────────────────────────────┘
```

## Component Design

### 1. MultiQueryExpander

**File**: `src/ticketpilot/retrieval/query_expander.py`

```python
class MultiQueryExpander:
    """Generate query variants using LLM for improved recall."""

    def __init__(self, llm_client=None, num_variants: int = 2):
        self._llm = llm_client  # Reuse DraftAgent's LLM config
        self._num_variants = num_variants

    def expand(self, query: str, intent: str = "") -> list[str]:
        """Return [original_query, variant_1, variant_2, ...].

        On LLM failure, returns [original_query] only.
        """
```

**LLM Prompt**:
```
你是一个搜索查询优化器。给定一个客服工单查询，生成 {n} 个不同角度的搜索关键词变体。
要求：每个变体 5-15 个字，覆盖不同语义角度（同义词、上位词、具体化）。
只输出 JSON 数组，不要解释。

查询：{query}
意图：{intent}
```

**输出**: `["退款到账时间", "退款进度查询"]`

**Fallback chain**:
1. LLM 成功 → 返回变体
2. LLM 超时/报错 → 返回 `[original_query]` + 日志警告
3. 无 API key → 跳过扩展，返回 `[original_query]`

### 2. ResultMerger

**File**: `src/ticketpilot/retrieval/result_merger.py`

```python
def merge_retrieval_results(
    result_sets: list[list[FusedResult]],
    strategy: str = "max_score",  # or "sum_score", "rrf_again"
) -> list[FusedResult]:
    """Merge multiple retrieval result sets, deduplicating by chunk_id.

    strategy="max_score": keep highest RRF score per chunk_id
    strategy="sum_score": sum RRF scores across queries (boosts docs found by multiple queries)
    strategy="rrf_again": treat each query as a ranker, apply second-level RRF
    """
```

**推荐策略**: `sum_score` — 被多个查询变体命中的文档得分更高（类似 PageIndex 的多路径验证思想）。

### 3. HybridReranker

**File**: `src/ticketpilot/retrieval/hybrid_reranker.py`（替代现有 `reranker.py`）

```python
@dataclass
class RerankSignal:
    """One scoring signal with its weight and raw/normalized values."""
    name: str
    weight: float
    raw_value: float
    normalized_value: float
    contribution: float  # weight * normalized_value

@dataclass
class RerankResult:
    """Reranked result with signal breakdown."""
    chunk_id: UUID
    final_score: float
    signals: list[RerankSignal]
    rank: int

class HybridReranker:
    """Multi-signal reranker combining RRF, embedding, intent, and content signals."""

    def __init__(self, config: RerankerConfig | None = None):
        self._config = config or RerankerConfig.default()

    def rerank(
        self,
        candidates: list[FusedResult],
        query: str,
        query_embedding: list[float] | None,
        intent: IntentClass | None,
        top_k: int = 10,
    ) -> list[RerankResult]:
        """Rerank candidates using weighted multi-signal fusion."""
```

#### Signal 1: RRF Score (weight: 0.4)
- 直接使用现有 RRF score
- Min-max normalization: `(score - min) / (max - min)`

#### Signal 2: Embedding Similarity (weight: 0.25)
- cosine_similarity(query_embedding, doc_embedding)
- 需要真实 embedding 才有意义
- FakeEmbedding 时此信号权重自动降为 0，重新分配

#### Signal 3: Intent Metadata Boost (weight: 0.2)
- 基于 `IntentClass` → `doc_type` 匹配表
- 匹配: +1.0, 不匹配: 0.0
- 二值信号，不做连续打分

#### Signal 4: Content Quality (weight: 0.15)
- `length_score`: 内容长度适中（200-800字）得分最高，太短/太长扣分
- `keyword_density`: 查询关键词在内容中的命中比例
- 两个子信号取平均

#### Weight Auto-adjustment
```python
def _adjust_weights(self, has_real_embedding: bool) -> dict[str, float]:
    """Redistribute weights when signals are unavailable."""
    weights = self._config.weights.copy()
    if not has_real_embedding:
        # Remove embedding signal, redistribute proportionally
        embedding_weight = weights.pop("embedding_similarity")
        total = sum(weights.values())
        weights = {k: v / total * 1.0 for k, v in weights.items()}
    return weights
```

### 4. RerankerConfig

**File**: `src/ticketpilot/retrieval/reranker_config.py`

```python
@dataclass
class RerankerConfig:
    weights: dict[str, float]  # signal_name -> weight
    intent_boost_table: dict[str, dict[str, float]]  # intent -> {doc_type: boost}
    content_quality: ContentQualityConfig
    enable_llm_scoring: bool = False  # Phase 2: LLM-based relevance

    @classmethod
    def default(cls) -> "RerankerConfig":
        """Default config with balanced weights."""

    @classmethod
    def from_yaml(cls, path: str) -> "RerankerConfig":
        """Load from config file for A/B experiments."""
```

**Config file**: `config/reranker.yaml`
```yaml
weights:
  rrf_score: 0.40
  embedding_similarity: 0.25
  intent_metadata_boost: 0.20
  content_quality: 0.15

intent_boost:
  refund:
    policy: 0.15
    faq: 0.10
  complaint:
    case: 0.15
    policy: 0.10
  # ...

content_quality:
  optimal_length_min: 200
  optimal_length_max: 800
  keyword_density_weight: 0.5
```

### 5. RetrievalTrace 扩展

现有 `RetrievalTrace` 新增字段：

```python
@dataclass
class RetrievalTrace:
    # ... existing fields ...

    # New fields for hybrid reranking
    query_variants: list[str] | None = None  # 扩展查询列表
    expansion_latency_ms: int = 0
    merged_result_count: int = 0  # 去重后候选数
    rerank_signals: list[dict] | None = None  # 每个结果的信号分解
    reranker_weights: dict[str, float] | None = None  # 实际使用的权重
    has_real_embedding: bool = False  # 是否使用真实 embedding
```

### 6. Pipeline 集成

修改 `src/ticketpilot/retrieval/pipeline.py`:

```python
def hybrid_retrieval(
    query: str,
    top_k: int = 10,
    intent: IntentClass | None = None,  # NEW: 用于 intent boost
    # ... existing params ...
    enable_query_expansion: bool = True,  # NEW: 多查询扩展开关
    reranker_config: RerankerConfig | None = None,  # NEW: 重排配置
) -> RetrievalTrace:
    """Enhanced hybrid retrieval with multi-query expansion and hybrid reranking."""

    # Step 0: Query expansion (optional)
    if enable_query_expansion:
        expander = MultiQueryExpander()
        queries = expander.expand(query, intent.value if intent else "")
    else:
        queries = [query]

    # Step 1-3: Parallel retrieval per query
    all_fused = []
    for q in queries:
        trace_q = _single_query_retrieval(q, top_k, doc_types, ...)
        all_fused.append(trace_q.fused_results)

    # Step 4: Merge + dedup
    merged = merge_retrieval_results(all_fused, strategy="sum_score")

    # Step 5: Hybrid rerank
    reranker = HybridReranker(config=reranker_config)
    reranked = reranker.rerank(
        candidates=merged,
        query=query,
        query_embedding=query_embedding,
        intent=intent,
        top_k=top_k,
    )

    # Step 6: Build trace
    return RetrievalTrace(...)
```

## File Manifest

| File | Action | Description |
|------|--------|-------------|
| `src/ticketpilot/retrieval/query_expander.py` | NEW | MultiQueryExpander |
| `src/ticketpilot/retrieval/result_merger.py` | NEW | Result merge + dedup |
| `src/ticketpilot/retrieval/hybrid_reranker.py` | NEW | 多信号混合重排器 |
| `src/ticketpilot/retrieval/reranker_config.py` | NEW | 重排配置 dataclass |
| `config/reranker.yaml` | NEW | 默认权重配置 |
| `src/ticketpilot/retrieval/pipeline.py` | MODIFY | 集成 expansion + hybrid rerank |
| `src/ticketpilot/retrieval/traces.py` | MODIFY | 新增 trace 字段 |
| `src/ticketpilot/retrieval/retrieve_evidence.py` | MODIFY | 传递 intent 参数 |
| `tests/unit/test_query_expander.py` | NEW | 查询扩展单元测试 |
| `tests/unit/test_result_merger.py` | NEW | 结果合并单元测试 |
| `tests/unit/test_hybrid_reranker.py` | NEW | 混合重排单元测试 |
| `tests/unit/test_pipeline_retrieval.py` | MODIFY | 更新 pipeline 测试 |
| `reports/retrieval/hybrid_rerank_comparison.md` | NEW | before/after 对比报告 |

## Compatibility

- `retrieve_evidence()` 接口向后兼容：新增 `intent` 参数，可选
- `hybrid_retrieval()` 接口向后兼容：新增参数均有默认值
- FakeEmbeddingProvider 继续作为无网络 fallback
- 现有 RetrievalTrace 消费者（dashboard, evaluation）不受影响（新字段都是 Optional）
- `reranker.py` 保留不删除（`rerank_with_embeddings` 和 `rerank_with_cross_encoder`），新 reranker 是独立模块

## Safety Constraints

- 多查询扩展 LLM 调用失败必须 graceful fallback（返回原始查询）
- HybridReranker 权重总和必须 = 1.0（运行时校验）
- 无真实 embedding 时自动降级（embedding 信号权重归零重新分配）
- 所有配置通过 YAML 文件管理，不硬编码
- 质量门必须通过
