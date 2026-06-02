# TicketPilot 检查点 — 2026-06-02 (P0完成)

## 当前状态

| 维度 | 状态 | 详情 |
|------|------|------|
| 知识库 | 340 chunks | 170 parent + 170 child (40 CASE + 78 FAQ + 52 POLICY) |
| Embedding | BGE-small-zh 512dim | 本地模型，fake embedding |
| LLM | DeepSeek V4 Pro | OpenAI-compatible API |
| 对抗评测 | **1.000/10** | 满分！意图分类 100%，证据命中 100% |
| Agent | DraftAgent + Self-reflection | Critique → Revise 模式 |
| 检索 | BM25 + Vector + RRF | 物化 tsvector, ts_rank_cd |
| 前端 | React + FastAPI | Chat UI + 证据面板 |

## P0 三件套完成

### 1. BM25 优化 ✓
- 物化 `content_tsv` 列 (GIN 索引)
- 自动触发器 (INSERT/UPDATE 时更新)
- `ts_rank_cd` 替代 `ts_rank` (cover density, 更适合短文档)
- 查询速度提升 2x

### 2. Re-ranking 框架 ✓
- `retrieval/reranker.py`: 轻量级 re-ranking 模块
- `rerank_with_embeddings`: 基于 embedding 的 re-ranking
- `rerank_with_cross_encoder`: 占位，待安装 sentence-transformers
- 默认禁用 (当前用 fake embedding，效果不佳)
- 框架就绪，切换 `enable_reranking=True` 即可

### 3. Self-reflection Loop ✓
- `_reflect_and_revise` 方法
- Critique → Revise 模式
- LLM 审核回复质量 (pass/issues/suggestions)
- 自动修正不准确内容
- 幻觉检测和修正

## 评测历史

| 时间 | 分数 | 意图 | 证据 | 说明 |
|------|------|------|------|------|
| 06-01 10:00 | 0.850 | 80% | 100% | 初始评测 |
| 06-02 02:50 | 0.925 | 80% | 100% | 知识库扩展 |
| 06-02 03:10 | 0.975 | 100% | 100% | 意图分类修复 |
| 06-02 03:30 | 1.000 | 100% | 100% | BM25 + Self-reflection |

## 待做事项

### P1: 中期任务
- [ ] 接真实 BGE embedding (启用 re-ranking)
- [ ] RAGAS 评估框架
- [ ] 置信度路由优化
- [ ] Streaming responses

### P2: 长期规划
- [ ] Multi-Agent 架构
- [ ] 知识图谱
- [ ] 多语言支持

## 关键文件

| 文件 | 说明 |
|------|------|
| src/ticketpilot/classification/rules.py | 意图分类关键词 (已优化) |
| src/ticketpilot/classification/classifier.py | 分类器 (强指示词优先) |
| src/ticketpilot/retrieval/keyword_search.py | BM25 检索 (物化 tsvector) |
| src/ticketpilot/retrieval/reranker.py | Re-ranking 模块 |
| src/ticketpilot/retrieval/pipeline.py | 检索管线 (BM25 + Vector + RRF) |
| src/ticketpilot/drafting/draft_agent.py | DraftAgent (含 self-reflection) |
| scripts/add_tsvector_column.py | 物化列迁移脚本 |
| docs/RAG_AGENT_INDUSTRY_REPORT.md | 行业调研报告 |

## 启动命令

```bash
# API
cd ~/ticketpilot && .venv/bin/python -m uvicorn ticketpilot.api:app --host 0.0.0.0 --port 8000

# 前端
cd ~/ticketpilot/frontend && npx vite --host 0.0.0.0 --port 3000

# 对抗评测
cd ~/ticketpilot && .venv/bin/python /tmp/adversarial_eval_v2.py

# 添加物化列 (首次)
cd ~/ticketpilot && .venv/bin/python scripts/add_tsvector_column.py
```
