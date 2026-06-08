# Tasks: Hybrid Retrieval Reranking

## Phase 1: RerankerConfig + 配置文件 (30 min)

### Task 1.1: Create `reranker_config.py`
- [ ] `RerankerConfig` dataclass: weights, intent_boost_table, content_quality
- [ ] `ContentQualityConfig` dataclass: optimal_length_min/max, keyword_density_weight
- [ ] `RerankerConfig.default()` class method
- [ ] `RerankerConfig.from_yaml(path)` class method
- [ ] `validate()` 方法：校验权重总和 = 1.0
- [ ] Unit tests: 默认配置、YAML 加载、权重校验

### Task 1.2: Create `config/reranker.yaml`
- [ ] 默认权重: rrf_score=0.40, embedding_similarity=0.25, intent_metadata_boost=0.20, content_quality=0.15
- [ ] Intent boost 表: 8 个 IntentClass × 优先 doc_type
- [ ] Content quality 参数: optimal_length_min=200, optimal_length_max=800
- [ ] Unit test: YAML 可解析且权重合法

## Phase 2: HybridReranker 核心 (45 min)

### Task 2.1: Create `hybrid_reranker.py` — Signal 1 (RRF Score)
- [ ] `RerankSignal` dataclass: name, weight, raw_value, normalized_value, contribution
- [ ] `RerankResult` dataclass: chunk_id, final_score, signals, rank
- [ ] `HybridReranker.rerank()` 骨架
- [ ] Signal 1: RRF score min-max normalization
- [ ] Unit test: 单信号 rerank 结果 = RRF 排序

### Task 2.2: Signal 2 (Embedding Similarity)
- [ ] cosine_similarity 计算（复用 reranker.py 现有函数）
- [ ] 从 DB 获取 doc embedding（复用 `_get_document_embedding`）
- [ ] FakeEmbedding 检测：自动降级（权重归零重分配）
- [ ] Unit test: 真实 embedding 时相似度参与打分；fake 时自动降级

### Task 2.3: Signal 3 (Intent Metadata Boost)
- [ ] `intent_boost_table` 查询逻辑
- [ ] IntentClass → doc_type 匹配 → 加分
- [ ] Unit test: 退款意图 + policy 文档 → +0.15；退款意图 + logistics 文档 → 0

### Task 2.4: Signal 4 (Content Quality)
- [ ] `length_score`: 正态分布曲线，optimal_length 中心峰值最高
- [ ] `keyword_density`: 查询词在 content 中的命中比例
- [ ] 两个子信号取平均作为 content_quality signal
- [ ] Unit test: 短/中/长内容得分差异；高/低关键词密度得分差异

### Task 2.5: Weight Auto-adjustment + Integration
- [ ] `_adjust_weights()`: 信号不可用时重新分配权重
- [ ] 4 信号加权求和 → final_score
- [ ] 结果按 final_score 降序排列，赋 rank
- [ ] Unit test: 权重总和始终 = 1.0；4 信号融合正确

## Phase 3: MultiQueryExpander (30 min)

### Task 3.1: Create `query_expander.py`
- [ ] `MultiQueryExpander` class
- [ ] LLM prompt 模板（中文，JSON 输出）
- [ ] `expand()` → `[original, variant_1, variant_2]`
- [ ] JSON 解析 + 校验（长度、数量）
- [ ] Fallback: LLM 失败 → `[original]` + 日志警告
- [ ] Unit test: 正常扩展、LLM 失败 fallback、无 API key 跳过

## Phase 4: ResultMerger (20 min)

### Task 4.1: Create `result_merger.py`
- [ ] `merge_retrieval_results(result_sets, strategy="sum_score")`
- [ ] `sum_score`: 同一 chunk_id 在多路结果中得分求和
- [ ] `max_score`: 取最高 RRF score
- [ ] `rrf_again`: 对多路排名做二次 RRF
- [ ] Dedup by chunk_id，保留最高分版本的 content
- [ ] Unit test: 3 路结果合并去重；sum_score 加分逻辑

## Phase 5: Pipeline 集成 (30 min)

### Task 5.1: 修改 `traces.py`
- [ ] 新增字段: query_variants, expansion_latency_ms, merged_result_count
- [ ] 新增字段: rerank_signals, reranker_weights, has_real_embedding
- [ ] 所有新字段 Optional，默认 None/0/False
- [ ] 现有测试不受影响

### Task 5.2: 修改 `pipeline.py`
- [ ] `hybrid_retrieval()` 新增参数: intent, enable_query_expansion, reranker_config
- [ ] Step 0: query expansion (if enabled)
- [ ] Step 1-3: 并行检索 per query variant
- [ ] Step 4: merge_retrieval_results
- [ ] Step 5: HybridReranker.rerank (替代现有 rerank_with_embeddings)
- [ ] Step 6: 构建扩展 trace
- [ ] 向后兼容：新参数都有默认值，现有调用不受影响

### Task 5.3: 修改 `retrieve_evidence.py`
- [ ] 新增 `intent` 参数传递到 `hybrid_retrieval()`
- [ ] 向后兼容：intent 默认 None

### Task 5.4: 更新现有测试
- [ ] `test_pipeline_retrieval.py`: 新增 hybrid rerank 路径测试
- [ ] `test_retrieve_evidence.py`: 新增 intent 传递测试
- [ ] 所有现有测试必须继续通过

## Phase 6: Evaluation + Report (30 min)

### Task 6.1: Before/After 对比
- [ ] 用现有 101 eval tickets 跑 before（当前 pipeline）
- [ ] 跑 after（hybrid reranker）
- [ ] 对比指标: Top-3 hit rate, Top-5 hit rate, MRR
- [ ] 输出 `reports/retrieval/hybrid_rerank_comparison.md`

### Task 6.2: 质量门
- [ ] `ruff check` 通过
- [ ] `pytest` 全部通过
- [ ] `openspec validate --all` 通过
- [ ] Secret scan 通过

## Total Estimated Time: ~3 hours
