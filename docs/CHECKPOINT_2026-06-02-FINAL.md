# TicketPilot 检查点 — 2026-06-02 (最终版)

## 项目概况

TicketPilot 是跨境电商客服 AI Copilot，基于 RAG + Agent 架构，提供智能客服回复生成能力。

**技术栈**: FastAPI + PostgreSQL + pgvector + DashScope Embedding + DeepSeek LLM

**评测分数**: 1.000 (满分)
**意图分类**: 100% (10/10)
**证据命中**: 100% (10/10)

---

## 核心架构

```
┌─────────────────────────────────────────────────────────┐
│                    Agent Harness                         │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │ Tracing  │ │ Eval     │ │ Guardrails│ │ Docker   │  │
│  │ (Phase1) │ │ (Phase2) │ │ (Phase3) │ │ (Phase4) │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
│                      ↓                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Multi-Agent Orchestrator             │  │
│  │  Refund | Complaint | Logistics | Technical      │  │
│  └──────────────────────────────────────────────────┘  │
│                      ↓                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │              DraftAgent + Self-Reflection         │  │
│  │  Retrieve → Evaluate → Generate → Reflect → Verify│  │
│  └──────────────────────────────────────────────────┘  │
│                      ↓                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │              Hybrid Retrieval                     │  │
│  │  BM25 + Vector (DashScope 1024d) + RRF + Rerank  │  │
│  └──────────────────────────────────────────────────┘  │
│                      ↓                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │              PostgreSQL + pgvector                │  │
│  │              340 knowledge chunks                 │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 知识库状态

| 类型 | 数量 | 说明 |
|------|------|------|
| FAQ | 78 | 常见问题解答 |
| POLICY | 52 | 平台政策规则 |
| CASE | 40 | 客服处理案例 |
| **总计** | **170 条** | **340 chunks (parent + child)** |

**Embedding**: DashScope text-embedding-v3, 1024 维

---

## 检索系统

| 组件 | 技术 | 状态 |
|------|------|------|
| 全文检索 | PostgreSQL FTS (物化 tsvector) | ✓ |
| 向量检索 | pgvector HNSW (DashScope 1024d) | ✓ |
| 融合 | RRF (Reciprocal Rank Fusion) | ✓ |
| Re-ranking | RRF tiebreaker 策略 | ✓ |

**查询性能**: ~7ms (物化 tsvector 2x 加速)

---

## Agent 系统

### Multi-Agent 架构

| Agent | 路由条件 | 特殊处理 |
|-------|----------|----------|
| RefundAgent | refund, return_exchange | - |
| ComplaintAgent | complaint | 强制人工审核 |
| LogisticsAgent | logistics | - |
| TechnicalAgent | technical_issue, account_issue | - |
| DefaultAgent | 其他 | - |

### DraftAgent 流程

1. **Retrieve**: 检索知识库
2. **Evaluate**: 评估证据质量
3. **Reformulate**: 必要时重构查询
4. **Generate**: 生成回复
5. **Reflect**: 自我反思和修正
6. **Verify**: 最终验证

---

## 安全护栏

| 检查项 | 说明 | 状态 |
|--------|------|------|
| PII 检测 | 手机号、身份证、邮箱 | ✓ |
| 幻觉检测 | 强声明、具体数字 | ✓ |
| 输入验证 | 注入检测、长度检查 | ✓ |
| 置信度路由 | >0.8 自主, <0.6 强制人工 | ✓ |

---

## 可观测性

| 能力 | 说明 | 状态 |
|------|------|------|
| 追踪 | 完整链路追踪 (logs/traces/) | ✓ |
| 评估 | RAGAS 框架 (evaluation/agent_eval.py) | ✓ |
| 指标 | 意图准确率、证据命中率、忠实度 | ✓ |

---

## 部署配置

### 本地开发

```bash
cd ~/ticketpilot
.venv/bin/python -m uvicorn ticketpilot.api:app --host 0.0.0.0 --port 8000
```

### Docker 部署

```bash
cd ~/ticketpilot
docker compose up -d
```

**服务**:
- PostgreSQL + pgvector (port 5432)
- TicketPilot API (port 8000)

---

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/chat` | POST | 聊天接口 |
| `/api/chat/stream` | POST | 流式聊天 (SSE) |
| `/api/tickets` | POST | 工单处理 |
| `/api/reviews` | POST | 审核决策 |
| `/api/evaluation` | GET | 评估指标 |

---

## 评测历史

| 时间 | 改进 | 分数 | 意图 | 证据 |
|------|------|------|------|------|
| 06-01 10:00 | 初始 | 0.850 | 80% | 100% |
| 06-02 02:50 | 知识库扩展 | 0.925 | 80% | 100% |
| 06-02 03:10 | 意图分类 | 0.975 | 100% | 100% |
| 06-02 03:30 | BM25 | 1.000 | 100% | 100% |
| 06-02 03:45 | Self-reflection | 1.000 | 100% | 100% |
| 06-02 04:00 | 置信度路由 | 1.000 | 100% | 100% |
| 06-02 04:30 | 真实 Embedding | 0.950 | 100% | 100% |
| 06-02 05:00 | Agent Harness P1 | 0.975 | 100% | 100% |
| 06-02 05:30 | Agent Harness P2 | 0.975 | 100% | 100% |
| 06-02 06:00 | Agent Harness P3 | 1.000 | 100% | 100% |
| 06-02 06:30 | Re-ranking 优化 | 1.000 | 100% | 100% |
| 06-02 07:00 | Docker 部署 | 1.000 | 100% | 100% |
| 06-02 07:30 | Multi-Agent | 1.000 | 100% | 100% |

**总提升**: 0.850 → 1.000 (+17.6%)

---

## 关键文件索引

| 文件 | 说明 |
|------|------|
| `src/ticketpilot/api/__init__.py` | FastAPI 端点 |
| `src/ticketpilot/api/streaming.py` | SSE 流式端点 |
| `src/ticketpilot/multi_agent/__init__.py` | Multi-Agent 编排器 |
| `src/ticketpilot/drafting/draft_agent.py` | DraftAgent |
| `src/ticketpilot/retrieval/pipeline.py` | 检索管线 |
| `src/ticketpilot/retrieval/keyword_search.py` | BM25 检索 |
| `src/ticketpilot/retrieval/reranker.py` | Re-ranking |
| `src/ticketpilot/classification/rules.py` | 意图分类规则 |
| `src/ticketpilot/classification/classifier.py` | 分类器 |
| `src/ticketpilot/tracing/__init__.py` | 追踪模块 |
| `src/ticketpilot/guardrails/__init__.py` | 护栏模块 |
| `src/ticketpilot/evaluation/agent_eval.py` | 评估框架 |
| `scripts/rebuild_embeddings_curl.py` | Embedding 重建 |
| `scripts/run_agent_eval.py` | 评估脚本 |
| `data/eval/agent_eval_dataset.json` | 评估数据集 |
| `Dockerfile` | Docker 镜像 |
| `docker-compose.yml` | Docker 编排 |
| `README.md` | 项目文档 |
| `docs/IMPROVEMENT_TRACKING.md` | 改进追踪 |
| `docs/AGENT_HARNESS_REPORT.md` | Agent Harness 报告 |

---

## 启动命令

```bash
# 本地开发
cd ~/ticketpilot
.venv/bin/python -m uvicorn ticketpilot.api:app --host 0.0.0.0 --port 8000

# 前端 (单独终端)
cd ~/ticketpilot/frontend
npx vite --host 0.0.0.0 --port 3000

# Docker 部署
cd ~/ticketpilot
docker compose up -d

# 运行评测
.venv/bin/python /tmp/adversarial_eval_v2.py

# 重建 Embedding
.venv/bin/python scripts/rebuild_embeddings_curl.py

# 查看追踪
ls logs/traces/
```

---

## 下一步建议

1. **知识库扩展**: 补充支付问题相关知识 (ADV-008)
2. **前端集成**: React 前端对接 SSE 流式接口
3. **生产部署**: 配置域名、SSL、监控
4. **持续优化**: 根据 trace 分析优化 Agent 性能
