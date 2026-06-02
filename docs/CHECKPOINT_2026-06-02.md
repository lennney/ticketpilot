# TicketPilot 检查点 — 2026-06-02

## 当前状态

| 维度 | 状态 | 详情 |
|------|------|------|
| 知识库 | 340 chunks | 170 parent + 170 child (40 CASE + 78 FAQ + 52 POLICY) |
| Embedding | BGE-small-zh 512dim | 本地模型，340 chunks 全部有 embedding |
| LLM | DeepSeek V4 Pro | OpenAI-compatible API |
| 对抗评测 | 0.925/10 | 证据命中率 100%，意图分类 80% |
| Agent | DraftAgent 已实现 | 多步推理、自主检索、自检 |
| 前端 | React + FastAPI | Chat UI + 证据面板 |

## 今天的优化记录

### 1. 知识库扩展 (144 → 340 chunks)
- 导入 `cross_border_generated.json` 的 36 条结构化知识
- FAQ: 33 → 78 (+45)
- POLICY: 19 → 52 (+33)
- CASE: 20 → 40 (+20)
- 使用 SHA-256 哈希（满足 DB 约束）
- 修复了 CASE 条目的字段映射（issue_summary + resolution）

### 2. 评测结果提升
- 入库前: 0.850/10
- 入库后: 0.925/10 (+8.8%)
- 意图分类准确率: 80% (8/10)
- 证据命中率: 100% (10/10)

### 3. 失败案例分析
- ADV-005: "发错货+三倍赔偿" → 预期 complaint, 实际 return_exchange
  - 原因: "发错货"触发了退货分类
  - 修复建议: 在 complaint 规则中添加"三倍赔偿"关键词

- ADV-008: "支付失败但扣款" → 预期 technical_issue, 实际 other
  - 原因: rules.py 没有覆盖支付扣款场景
  - 修复建议: 添加 payment_failed 相关关键词

## 待做事项

### P0: 意图分类优化
- [ ] 在 rules.py 的 COMPLAINT 规则中添加"三倍赔偿"
- [ ] 添加 PAYMENT_ISSUE 意图分类（或归入 TECHNICAL_ISSUE）
- [ ] 重跑评测验证修复效果

### P1: 知识库继续扩展
- [ ] 修复 DeepSeek API key（当前 401 Unauthorized）
- [ ] 从 28 个爬取页面提取更多知识
- [ ] 目标: 200+ 条知识

### P1: RRF 权重调优
- [ ] 调整 keyword_weight=1.5, embedding_weight=0.8
- [ ] 评测对比

### P2: Agent 评测
- [ ] 更新评测脚本使用 DraftAgent
- [ ] 跑完整对抗评测

## 关键文件

| 文件 | 说明 |
|------|------|
| src/ticketpilot/classification/rules.py | 意图分类关键词 |
| scripts/import_generated_knowledge.py | 知识入库脚本 |
| data/knowledge/external/cross_border_generated.json | 36条结构化知识 |
| reports/eval/adversarial_eval_v1.json | 评测报告 |

## 启动命令

```bash
# API
cd ~/ticketpilot && .venv/bin/python -m uvicorn ticketpilot.api:app --host 0.0.0.0 --port 8000

# 前端
cd ~/ticketpilot/frontend && npx vite --host 0.0.0.0 --port 3000

# 对抗评测
cd ~/ticketpilot && .venv/bin/python /tmp/adversarial_eval_v2.py
```
