# Proposal: Hybrid Retrieval Reranking

## Executive Summary

TicketPilot 当前检索管线：keyword FTS + pgvector HNSW → RRF fusion → embedding tiebreaker rerank。Phase 8 已实现 OpenAICompatibleProvider 但默认仍是 FakeEmbeddingProvider，reranker 只用 embedding 相似度做 tiebreaker，cross-encoder 是空 TODO。

本次改造引入**混合重排器（Hybrid Reranker）**：在 RRF fusion 之后，用多信号加权融合替代单一 embedding tiebreaker，显著提升 Top-K 排序质量。同时加入**多查询扩展**提升召回率。

灵感来源：PageIndex 的 LLM 树搜索思路，但适配 TicketPilot 的客服场景——不需要建树（文档短），而是用 LLM 做查询扩展和相关性评分。

## Baseline (Current State)

### Retrieval Pipeline
```
Query → build_retrieval_query (静态意图词映射, _INTENT_TERMS 硬编码)
      → keyword_search (PostgreSQL FTS 'simple' + 32个业务词 LIKE 兜底)
      → vector_search (pgvector HNSW, FakeEmbedding 384-dim)
      → RRF fusion (k=60)
      → rerank_with_embeddings (embedding相似度作tiebreaker, 无实际语义)
      → top_k output
```

### Known Gaps
1. **FakeEmbedding 无语义**: 向量搜索路输出随机排序，RRF 有一半输入是噪声
2. **静态查询扩展**: `_INTENT_TERMS` 硬编码，"退款"↔"退钱"↔"返还费用" 无法覆盖
3. **Reranker 弱**: 仅 embedding tiebreaker，cross-encoder 是空 TODO
4. **无意图感知排序**: 退款工单检索到物流文档不会被降权
5. **无查询多样性**: 单一查询表达，语义变体覆盖不足

## Goal

1. 实现 **HybridReranker**：多信号加权融合（RRF score + embedding similarity + intent metadata boost + content quality signal）
2. 实现 **MultiQueryExpander**：基于 LLM 生成 2-3 个查询变体，并行检索后合并去重
3. 接入真实 embedding 作为默认（保留 FakeEmbedding 用于无网络测试）
4. 所有新信号记录到 RetrievalTrace，支持调试和评估
5. 用现有 101 eval tickets 做 before/after 对比

## Non-goals

- ❌ 不做 PageIndex 树搜索（TicketPilot 文档平均 500-1000 字，无需层级目录）
- ❌ 不做 cross-encoder reranker（需要 sentence-transformers 重依赖，与 uv 轻量原则冲突）
- ❌ 不改知识库 schema（不加文档摘要字段，留到下个迭代）
- ❌ 不改 DraftAgent 内部逻辑
- ❌ 不做 embedding fine-tuning
- ❌ 不做生产部署
- ❌ 不 commit API key

## Key Design Decisions

### A. Hybrid Reranker 信号融合

| 信号 | 权重范围 | 来源 | 说明 |
|------|----------|------|------|
| RRF score | 0.3-0.5 | 现有 | keyword + vector 融合排名 |
| Embedding similarity | 0.2-0.3 | 现有(需真实embedding) | query-document 语义相似度 |
| Intent metadata boost | 0.1-0.2 | 新增 | 意图分类→文档类型匹配加分 |
| Content quality signal | 0.05-0.1 | 新增 | 内容长度、关键词密度等启发式 |

权重通过配置文件管理，支持 A/B 实验。

### B. Intent Metadata Boost 逻辑

| IntentClass | 优先 doc_type | 加分 |
|-------------|--------------|------|
| REFUND | policy, faq | +0.15 |
| RETURN_EXCHANGE | policy, faq | +0.15 |
| COMPLAINT | case, policy | +0.15 |
| TECHNICAL_ISSUE | faq, case | +0.1 |
| ACCOUNT_ISSUE | policy, faq | +0.1 |
| LOGISTICS | faq, case | +0.1 |
| PRODUCT_CONSULTING | faq | +0.15 |
| OTHER | (无加分) | 0 |

### C. Multi-Query Expansion

```
原始查询: "我买的东西退款一直没到账"
    ↓ LLM expansion (DeepSeek-chat, temperature=0.5)
扩展查询: ["退款到账时间", "退款进度查询", "退款未收到怎么办"]
    ↓ 并行检索 (3路)
    ↓ RRF merge + dedup
    ↓ HybridReranker
最终 Top-K
```

- 每次扩展生成 2 个变体（控制 token 消耗）
- DeepSeek-chat 调用，单次 ~200 tokens，成本可忽略
- 扩展失败时 graceful fallback 到原始查询

### D. 真实 Embedding 策略

| 决策 | 选择 |
|------|------|
| 默认 provider | `EMBEDDING_PROVIDER` env var 控制，默认 `openai_compatible` |
| 无网络 fallback | 自动降级到 FakeEmbeddingProvider + 日志警告 |
| 模型 | `text-embedding-3-small` (1536-dim) 或 DashScope `text-embedding-v4` (1024-dim) |
| 索引重建 | 维度变更时自动检测 + 提示重建 |

## Proposed Metrics

| Metric | Definition | Baseline Target |
|--------|-----------|----------------|
| Top-3 hit rate | Top-3 检索命中 golden expected doc | 提升 10%+ |
| Top-5 hit rate | Top-5 检索命中 | 提升 8%+ |
| MRR | Mean Reciprocal Rank | 提升 15%+ |
| Intent-aware precision | 检索结果 doc_type 与意图匹配率 | 新指标 |
| Reranker latency | 单次重排耗时 | < 50ms (无LLM) / < 500ms (含LLM) |
| Query expansion coverage | 扩展查询召回原始查询未命中的文档比例 | 新指标 |

## Constraints

- FakeEmbeddingProvider 必须保留为无网络环境的 fallback
- HybridReranker 权重必须可配置（支持 A/B）
- 多查询扩展的 LLM 调用失败必须 graceful fallback
- 所有新信号必须记录到 RetrievalTrace
- 现有 101 eval tickets 不修改
- 质量门必须通过（ruff + tests + openspec）
- 无 API key commit
