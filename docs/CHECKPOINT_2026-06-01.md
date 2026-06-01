# TicketPilot 检查点 — 2026-06-01

## 当前状态

| 维度 | 状态 | 详情 |
|------|------|------|
| 知识库 | 144 chunks | 72 parent + 72 child (33 FAQ + 19 Policy + 20 Case) |
| Embedding | BGE-small-zh 512dim | 本地模型，144 chunks 全部有 embedding |
| LLM | DeepSeek V4 Pro | OpenAI-compatible API |
| 对抗评测 | 0.850/10 | 证据命中率 100%，引用格式 [1][2][3] |
| 意图分类 | 40% (待验证) | rules.py 已扩展关键词，尚未重跑评测 |
| Agent | DraftAgent 已实现 | 多步推理、自主检索、自检 |
| 前端 | React + FastAPI | Chat UI + 证据面板 |

## 今天的优化记录

### 1. 跨境电商方向确定
- 选跨境电商而非通用电商（差异化 + SEO 背景匹配 + 字节面试相关）
- 覆盖：海关清关、关税计算、跨境退货、物流丢件、食品安全、账号安全

### 2. 知识库构建
- 爬取 9 个真实政策页面（京东国际/天猫国际/海关总署/速卖通）
- DeepSeek 基于真实数据生成 36 条结构化知识
- stealth_fetch.py 爬取了 31 个页面（~80KB），已保存到 stealth_crawled/
- **待做：** 把爬取数据结构化 + 入库（目标 +50 条）

### 3. Parent-Child Chunking
- 每条知识拆分：parent（标题+摘要 50-100字）+ children（详细内容 100-200字）
- 144 chunks（72 parent + 72 child）

### 4. DraftAgent 实现
- draft_agent.py: 793 行
- 多步推理：检索→评估→决策→生成→自检
- 能自主决定是否需要补充检索

### 5. 检索优化
- BUSINESS_TERMS_LIKE 扩展到 50+ 个跨境电商关键词
- 关键词+embedding 混合检索 + RRF 融合

### 6. Bug 修复
- 分类器：first-match-wins（优先退款>投诉）
- 风险评估：12315/消费者协会/食品安全关键词
- Prompt：去掉"审核/草稿"，引用改为 [1][2][3]
- Validator：收紧 claim 关键词，减少误判

## 明天要做的事

### P0: 意图分类准确率
- [ ] 重跑对抗评测验证 rules.py 扩展效果
- [ ] 如果还是低，考虑用 LLM 做 fallback 分类（关键词匹配不到时用 DeepSeek 分类）

### P0: 知识库扩展
- [ ] 把 stealth_crawled/ 的 31 个页面结构化 + 入库
- [ ] 用 DeepSeek 从爬取内容提取 FAQ/Policy/Case
- [ ] 目标：从 72 条扩展到 150+ 条

### P1: RRF 权重调优
- [ ] 调整 keyword_weight=1.5, embedding_weight=0.8
- [ ] 评测对比

### P1: Agent 评测
- [ ] 更新评测脚本使用 DraftAgent（当前脚本用旧管线）
- [ ] 跑完整对抗评测

### P2: Embedding 升级（可选）
- [ ] bge-large-zh 或 bge-m3（多语言，适合跨境场景）

## 关键文件

| 文件 | 说明 |
|------|------|
| src/ticketpilot/drafting/draft_agent.py | Agent 核心 |
| src/ticketpilot/classification/rules.py | 意图分类关键词（已扩展） |
| src/ticketpilot/retrieval/keyword_search.py | 关键词检索（已扩展） |
| src/ticketpilot/drafting/llm_provider.py | LLM prompt（已优化） |
| src/ticketpilot/drafting/citation_validator.py | 引用验证（已收紧） |
| data/knowledge/external/stealth_crawled/ | 31 个爬取页面（待处理） |
| data/knowledge/external/cross_border_raw/ | 9 个原始政策页面 |
| data/knowledge/external/cross_border_generated.json | 36 条 LLM 生成知识 |
| reports/eval/adversarial_eval_v1.json | 评测报告 |
| docs/KNOWLEDGE_EXPANSION_PLAN.md | 知识库扩展计划 |
| docs/RETRIEVAL_AGENT_PLAN.md | 检索+Agent 方案 |

## 启动命令

```bash
# API
cd ~/ticketpilot && .venv/bin/python -m uvicorn ticketpilot.api:app --host 0.0.0.0 --port 8000

# 前端
cd ~/ticketpilot/frontend && npx vite --host 0.0.0.0 --port 3000

# 重建 embedding
cd ~/ticketpilot && .venv/bin/python scripts/rebuild_embeddings.py --confirm --allow-dimension-reset

# 对抗评测
cd ~/ticketpilot && .venv/bin/python /tmp/adversarial_eval_v2.py
```
