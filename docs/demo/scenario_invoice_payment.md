# Demo Scenario 3: 发票/支付争议 (Invoice + Payment Dispute)

> 支付扣款异常、发票开具失败、订单状态不一致等场景，是电商客服中高频但严重度较低的工单类型。这个 demo 展示 TicketPilot 在非高风险场景下的处理能力。

---

## 1. Scenario Purpose

这个 Demo 展示 TicketPilot 在 **发票 + 支付** 场景下的核心能力：

- **支付纠纷检测**：识别重复扣款、支付未到账、扣款金额异常
- **发票问题分类**：区分发票开具、发票更正、发票类型等不同诉求
- **适中风险判定**：POLICY_CONFLICT 或 INSUFFICIENT_EVIDENCE，LOW-MEDIUM severity
- **条件性人工审核**：无风险标记的纯咨询工单无需人工审核；有 PAYMENT_CONFLICT 或投诉语言时自动触发 must_human_review
- **证据检索**：优先检索支付政策、发票政策、支付案例
- **边界约束**：草稿不承诺退款或赔偿，仅解释政策

---

## 2. Example Tickets

### Ticket C1 — 重复扣款 + 订单未确认

```python
from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.schema.ticket import RawTicket
from datetime import datetime

ticket = RawTicket(
    original_text="我付款成功了但订单显示未支付，还重复扣了一笔，发票也开不出来。订单号：DEMO-PAY-001。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_C1"
)
result = intake_risk_pipeline(ticket)

print("=== 意图分类 ===")
print(f"意图: {result.classification.intent.value}")
print(f"置信度: {result.classification.confidence:.2f}")

print("\n=== 风险评估 ===")
print(f"严重程度: {result.risk_assessment.severity.value}")
print(f"风险标记: {[f.value for f in result.risk_assessment.flags]}")
print(f"需人工审核: {result.risk_assessment.must_human_review}")

print("\n=== 证据检索 ===")
for ec in result.evidence_candidates[:5]:
    print(f"  [{ec.doc_type.value}] score={ec.score:.4f} — {ec.content[:80]}")
```

### Ticket C2 — 发票开具要求

```python
ticket = RawTicket(
    original_text="我买了一批办公用品，需要开公司发票，订单号：DEMO-PAY-002。下单时选了个人，能改吗？",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_C2"
)
result = intake_risk_pipeline(ticket)

print(f"意图: {result.classification.intent.value}")
print(f"风险标记: {[f.value for f in result.risk_assessment.flags]}")
print(f"需人工审核: {result.risk_assessment.must_human_review}")
```

### Ticket C3 — 多扣款 + 账单争议

```python
ticket = RawTicket(
    original_text="订单DEMO-PAY-003显示金额是299，但信用卡扣了358，多收了59块。请核实退款，不然我要投诉。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_C3"
)
result = intake_risk_pipeline(ticket)

print(f"意图: {result.classification.intent.value}")
print(f"风险标记: {[f.value for f in result.risk_assessment.flags]}")
print(f"严重程度: {result.risk_assessment.severity.value}")
```

---

## 3. Expected Workflow

```
Ticket Intake
  → 原始文本规范化，提取订单号 DEMO-PAY-001/002/003
  → 客户标识 CUST_DEMO_Cx

Intent Classification
  → refund（扣款/退款）或 other（发票/账单）为主意图
  → "开发票""发票"等关键词映射到 invoice/billing 相关

Risk Assessment
  → C1: POLICY_CONFLICT（发票规则与用户期望冲突）
  → C2: 低风险，无风险标记或 INSUFFICIENT_EVIDENCE
  → C3: POLICY_CONFLICT + 包含"投诉"可能触发 COMPLAINT_RISK

Evidence Retrieval (Hybrid: Keyword + Vector)
  → 查询构建：发票 + 支付 + 扣款 + 重复付款 + 账单
  → 融合检索：FAQ + Policy + Case

Draft Reply
  → 基于发票政策和支付政策生成草稿
  → 说明发票更正流程或支付核查流程
  → 不主动承诺退款或补偿

Human Review
  → C1: policy_conflict 触发 → must_human_review = true
  → C2: 无风险标记 → must_human_review = false（纯咨询）
  → C3: policy_conflict + complaint_risk → must_human_review = true
  → 规则：存在任何风险标记即触发人工审核
```

---

## 4. Expected Risk Behavior

| 字段 | Ticket C1 | Ticket C2 | Ticket C3 |
|------|-----------|-----------|-----------|
| `expected_issue_type` | refund / other | other / refund | refund / complaint |
| `risk_flags` | policy_conflict | (none) / insufficient_evidence | policy_conflict, complaint_risk |
| `severity` | MEDIUM | LOW | MEDIUM |
| `must_human_review` | true | false | true |
| `fallback_required` | false | false | false |
| `no_auto_send` | true | true | true |

---

## 5. Expected Evidence Behavior

应优先检索的证据类型和代表性文档：

| Doc Type | Content | Supports |
|----------|---------|----------|
| POLICY | 发票开具规则 (`ad0d0d0d-3333-3333-3333-333333333333`) | 发票申请和更正 |
| POLICY | 重复付款处理规则 | 重复扣款退款流程 |
| POLICY | 支付异常核实规则 | 支付未到账处理 |
| CASE | 重复付款退款案 (`c6666666-6666-6666-6666-666666666666`) | 相似案例参考 |
| CASE | 发票争议案 (`c7777777-7777-7777-7777-777777777777`) | 发票修改案例 |
| FAQ | 发票 FAQ（如何申请、如何更改抬头） | 用户操作指引 |

---

## 6. Draft Boundary

- 系统**只生成草稿**，不自动发送
- 不承诺具体退款金额或时间
- 发票修改需用户提供税务信息，系统不代填
- 支付核查需用户配合提供银行流水，系统不单方面确认
- 存在风险标记（policy_conflict / complaint_risk）时触发人工审核
- 无风险标记的纯咨询工单（如发票开具咨询）无需人工审核

---

## 7. What This Demo Proves

| 能力 | 说明 |
|------|------|
| 非高风险场景处理 | 系统能区分高风险（投诉/隐私）和低风险（发票/支付）场景 |
| 条件性人工审核 | 无风险标记的纯咨询工单自动处理；有 risk flag 时触发人工审核 |
| 领域特定检索 | 发票/支付场景下优先检索对应 Policy 和 Case |
| 政策对齐 | 草稿基于发票政策生成，不与平台规则冲突 |
| 多意图区分 | 能区分"发票开具"和"支付争议"等不同诉求 |

---

## 8. Limitations

- **Synthetic scenario**：本 demo 使用的人工编写示例工单，不是真实客服数据
- **Not real enterprise validation**：场景覆盖不代表真实业务分布
- **Fake embedding**：当前使用确定性 fake embedding（384-dim 哈希），仅验证管道机械正确性，不提供语义检索质量
- **Template draft**：草稿基于模板生成，不调用 LLM，不是生产级回复质量
- **Local demo only**：系统是本地作品集演示项目，不是生产部署
- **Phase 8 deferred**：真实 embedding provider 对比验证保留到 Phase 8
- **No real payment/finance integration**：系统不连接真实支付或财务系统

---

> **详见：** [phase7_demo_scenarios.md](phase7_demo_scenarios.md) | [Demo Guide](README.md) | [Sample Tickets](sample_tickets.md)
