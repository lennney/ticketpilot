# TicketPilot Demo Guide

> 本地演示指南 — 三条演示线覆盖工单处理全流程
>
> **这是一个本地作品集演示，不是生产效果证明。**

## 目录

- [前置准备](#前置准备)
- [演示线 A：普通售后工单](#演示线-a普通售后工单)
- [演示线 B：高风险工单](#演示线-b高风险工单)
- [演示线 C：评测报告](#演示线-c评测报告)
- [演示要点](#演示要点)
- [常见问题](#常见问题)

---

## 前置准备

请先完成 README 中的 [Quick Start](../../README.md#6-快速开始) 步骤：

```bash
# 1. 克隆并安装依赖
git clone <repo-url>
cd ticketpilot
uv sync

# 2. 启动 PostgreSQL（需要 Docker）
docker compose up -d

# 3. 运行数据库迁移
alembic upgrade head

# 4. 导入种子知识
uv run python scripts/ingest_knowledge.py

# 5. 验证环境
./scripts/run_quality_gate.sh
```

质量门禁通过后即可开始演示。

---

## 演示线 A：普通售后工单

**目标：** 展示一个典型的退款/退货工单从接收到草稿回复的全流程。

### 步骤 1：启动人工审核控制台

```bash
uv run streamlit run src/ticketpilot/review/console.py
```

浏览器打开 http://localhost:8501。

### 步骤 2：提交一个退款工单

在终端中运行以下 Python 代码：

```python
from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.schema.ticket import RawTicket
from datetime import datetime

ticket = RawTicket(
    original_text="我要退款，订单号：123456，收到的商品有质量问题。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_001"
)
result = intake_risk_pipeline(ticket)

print("=== 意图分类 ===")
print(f"工单类型: {result.classification.intent.value}")
print(f"置信度: {result.classification.confidence:.2f}")

print("\n=== 风险评估 ===")
print(f"严重程度: {result.risk_assessment.severity.value}")
print(f"风险标记: {[f.value for f in result.risk_assessment.flags]}")
print(f"需要人工审核: {result.risk_assessment.must_human_review}")

print("\n=== 知识检索 ===")
for ec in result.evidence_candidates:
    print(f"  [{ec.doc_type.value}] {ec.content[:80]}... (score: {ec.score:.4f})")

print(f"\n检索追踪: {result.retrieval_trace.fusion_mode}")
```

**演示要点：**
- 展示 `issue_type` = `refund`，说明 8 类意图分类
- 展示 `severity` = `low`，解释 severity 判断逻辑
- 展示 `evidence_candidates` 来自 FAQ/Policy/Case 三种文档类型
- 如果开启了 DraftReply，展示草稿回复和证据引用
- 在 Streamlit 控制台中演示 Approve 操作

### 步骤 3：换一个退换货工单

```python
from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.schema.ticket import RawTicket
from datetime import datetime

ticket = RawTicket(
    original_text="我想退货换货，订单号：654321，尺码不合适。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_002"
)
result = intake_risk_pipeline(ticket)

print(f"工单类型: {result.classification.intent.value}")
print(f"严重程度: {result.risk_assessment.severity.value}")
```

**演示要点：**
- 退款和退换货的 `issue_type` 不同（`refund` vs `return_exchange`）
- 普通售后工单没有风险标记，`severity` = `low`
- 如果开启了 DraftReply，查看工单上下文是否被包含在草稿中

---

## 演示线 B：高风险工单

**目标：** 展示系统如何识别高风险工单并强制人工审核。

### 高风险投诉 + 赔偿（申诉）

```python
from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.schema.ticket import RawTicket
from datetime import datetime

ticket = RawTicket(
    original_text="客服态度太差了，我要投诉！要求3倍赔偿，不然我就找律师起诉你们。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_003"
)
result = intake_risk_pipeline(ticket)

print("=== 意图分类 ===")
print(f"工单类型: {result.classification.intent.value}")

print("\n=== 风险评估 ===")
print(f"严重程度: {result.risk_assessment.severity.value}")
print(f"风险标记: {[f.value for f in result.risk_assessment.flags]}")
print(f"需要人工审核: {result.risk_assessment.must_human_review}")

print("\n=== 检索结果 ===")
for ec in result.evidence_candidates:
    print(f"  [{ec.doc_type.value}] {ec.content[:80]}...")
```

**演示要点：**
- 展示多个风险标记：`complaint_risk` + `compensation_risk` + `legal_risk`
- `severity` 因多个风险标记升级为 `high`
- `must_human_review = true`
- 在 Streamlit 控制台中演示 Escalate 或 Reject 操作

### 隐私 / 账号安全

```python
from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.schema.ticket import RawTicket
from datetime import datetime

ticket = RawTicket(
    original_text="我的账号被冻结了，个人信息可能泄露了，手机号被他人使用。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_004"
)
result = intake_risk_pipeline(ticket)

print(f"工单类型: {result.classification.intent.value}")
print(f"风险标记: {[f.value for f in result.risk_assessment.flags]}")
print(f"需要人工审核: {result.risk_assessment.must_human_review}")
```

**演示要点：**
- `issue_type` = `account_issue`，风险标记 = `account_security_risk` + `privacy_risk`
- 隐私类工单触发 `must_human_review`

### 弱证据 / 无证据

```python
from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.schema.ticket import RawTicket
from datetime import datetime

ticket = RawTicket(
    original_text="退款。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_005"
)
result = intake_risk_pipeline(ticket)

print(f"工单类型: {result.classification.intent.value}")
print(f"风险标记: {[f.value for f in result.risk_assessment.flags]}")
print(f"需要人工审核: {result.risk_assessment.must_human_review}")
print(f"证据数: {len(result.evidence_candidates)}")
```

**演示要点：**
- 非常短的工单（仅"退款"两字）也能被分类
- 但可能触发 `insufficient_evidence` 风险标记
- 如果开启了 DraftReply，查看 fallback 回复内容
- 强调系统在没有足够证据时不会编造信息

---

## 演示线 C：评测报告

**目标：** 展示离线评估流水线。

### CSV 预测模式

```bash
uv run python scripts/run_eval.py \
  --tickets data/eval/tickets_eval.csv \
  --golden data/eval/golden_expectations.csv \
  --predictions data/eval/sample_predictions.csv \
  --out-json reports/eval/evaluation_report.json \
  --out-md reports/eval/evaluation_report.md
```

查看生成的报告：

```bash
cat reports/eval/evaluation_report.md
```

**演示要点：**
- 展示 7 项评估指标（intent_accuracy, severity_accuracy, risk flag F1, evidence_doc_type_recall, fallback_correctness, must_human_review_accuracy, no_auto_send_compliance）
- 说明评估基于 10 条种子工单，不是真实世界数据
- 强调 fake embedding 限制

### Pipeline 预测模式

```bash
uv run python scripts/run_eval.py \
  --tickets data/eval/tickets_eval.csv \
  --golden data/eval/golden_expectations.csv \
  --prediction-mode pipeline \
  --out-json reports/eval/current_pipeline_report.json \
  --out-md reports/eval/current_pipeline_report.md
```

查看生成的报告：

```bash
cat reports/eval/current_pipeline_report.md
```

**演示要点：**
- Pipeline 模式运行完整管道生成预测
- 对比 CSV 模式和 Pipeline 模式的结果差异
- 报告中明确标注了 Limitations：种子数据、fake embedding、非真实世界性能

---

## 演示要点

### 核心展示内容

| 能力 | 演示线 | 关键展示点 |
|------|--------|-----------|
| 意图分类 | A | 8 类分类、置信度 |
| 风险评估 | A/B | 8 种风险标记、severity、must_human_review |
| 分层检索 | A | FAQ/Policy/Case 三种文档、关键词+向量融合 |
| 草稿生成 | A/B | 证据引用、fallback 处理 |
| 人工审核 | A/B | Approve/Edit/Escalate/Reject 操作 |
| 评估流水线 | C | 7 项指标、CSV/Pipeline 两种模式 |
| 质量门禁 | — | 自动化验证流程 |

### 不得声称的内容

- ❌ 这不是生产级客服系统
- ❌ 不要声称真实语义检索质量（fake embeddings）
- ❌ 不要声称真实企业数据覆盖率（种子数据）
- ❌ 不要声称 LLM 能力（模板生成）
- ❌ 不要声称自动发送回复（no auto-send）

---

## 常见问题

### 数据库连接失败

确保 PostgreSQL 已启动：

```bash
docker compose ps
docker compose logs postgres
```

### 集成测试跳过

集成测试需要数据库连接。如果数据库不可用，测试会标记为跳过。
质量门禁将跳过视为失败，除非设置 `TICKETPILOT_SKIP_DB_TESTS=1`。

### Streamlit 无法启动

```bash
uv run streamlit run src/ticketpilot/review/console.py --logger.level=debug
```

### 评估报告路径

所有评估报告输出到 `reports/eval/` 目录：

- `evaluation_report.json` — CSV 模式 JSON 报告
- `evaluation_report.md` — CSV 模式 Markdown 报告
- `current_pipeline_report.json` — Pipeline 模式 JSON 报告
- `current_pipeline_report.md` — Pipeline 模式 Markdown 报告

---

*TicketPilot — 本地演示 / 作品集项目。详见 [README.md](../../README.md)。*
