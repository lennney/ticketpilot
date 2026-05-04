# Demo Scenario 1: 退款投诉 (Refund + Complaint)

> 退款需求叠加投诉、赔偿要求乃至法律威胁，是客服系统最典型的高风险场景之一。

---

## 1. Scenario Purpose

这个 Demo 展示 TicketPilot 在 **退款 + 投诉** 场景下的核心能力：

- **多意图识别**：从文本中区分退款诉求和投诉/赔偿/法律威胁
- **复合风险检测**：识别 COMPLAINT_RISK / COMPENSATION_RISK / LEGAL_RISK 等多个风险标记
- **风险严重度升级**：多个风险标记叠加自动升级为 HIGH severity
- **强制人工审核**：高风险场景自动强制 must_human_review
- **证据检索**：优先检索退款政策、投诉升级规则、赔偿案例
- **边界约束**：草稿回复不承诺具体赔偿金额，不自动发送

---

## 2. Example Tickets

### Ticket A1 — 退款不满 + 投诉

```python
from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.schema.ticket import RawTicket
from datetime import datetime

ticket = RawTicket(
    original_text="我申请退款三天了还没到账，订单号是DEMO-REFUND-001。你们再不处理我就投诉，还要赔偿。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_A1"
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

### Ticket A2 — 商品质量问题 + 法律威胁

```python
ticket = RawTicket(
    original_text="收到的手机是坏的，屏幕有裂痕，我要求全额退款加赔偿。如果今天不解决我就找律师起诉你们。订单号：DEMO-REFUND-002。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_A2"
)
result = intake_risk_pipeline(ticket)

print(f"意图: {result.classification.intent.value}")
print(f"风险标记: {[f.value for f in result.risk_assessment.flags]}")
print(f"严重程度: {result.risk_assessment.severity.value}")
print(f"需人工审核: {result.risk_assessment.must_human_review}")
```

### Ticket A3 — 重复付款 + 要求赔偿

```python
ticket = RawTicket(
    original_text="同一笔订单扣了我两次钱，订单号：DEMO-REFUND-003。马上退一赔一，不然我就要投诉到12315。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_A3"
)
result = intake_risk_pipeline(ticket)

print(f"意图: {result.classification.intent.value}")
print(f"风险标记: {[f.value for f in result.risk_assessment.flags]}")
```

---

## 3. Expected Workflow

```
Ticket Intake
  → 原始文本规范化，提取 DEMO-REFUND-001/002/003 等订单号
  → 客户标识 CUST_DEMO_Ax

Intent Classification
  → refund（退款）为主意图
  → 出现"投诉""赔偿""律师""起诉"等关键词时同时映射为 complaint 相关风险

Risk Assessment
  → 关键词规则触发多个风险标记

Evidence Retrieval (Hybrid: Keyword + Vector)
  → 查询构建：退款 + 投诉 + 赔偿 + 法律 + 补偿
  → 融合检索：FAQ + Policy + Case

Draft Reply
  → 基于检索到的政策条款生成草稿
  → 附证据引用，标注高风险警告

Human Review
  → must_human_review = true
  → 审核员操作：Approve / Edit / Escalate / Reject
```

---

## 4. Expected Risk Behavior

| 字段 | Ticket A1 | Ticket A2 | Ticket A3 |
|------|-----------|-----------|-----------|
| `expected_issue_type` | refund | refund / complaint | refund |
| `risk_flags` | complaint_risk, compensation_risk | complaint_risk, compensation_risk, legal_risk | complaint_risk, compensation_risk |
| `severity` | HIGH | HIGH | HIGH |
| `must_human_review` | true | true | true |
| `fallback_required` | false | false | false |
| `no_auto_send` | true | true | true |

---

## 5. Expected Evidence Behavior

应优先检索的证据类型和代表性文档：

| Doc Type | Content | Supports |
|----------|---------|----------|
| POLICY | 赔偿诉求处理规则 (`ae0e0e0e-1111-1111-1111-111111111111`) | 赔偿处理流程 |
| POLICY | 投诉升级规则 (`ad0d0d0d-8888-8888-8888-888888888888`) | 投诉升级 |
| POLICY | 法律威胁与律师函处理规则 (`ad0d0d0d-9999-9999-9999-999999999999`) | 法律威胁响应 |
| CASE | 律师函赔偿案 (`c1111111-1111-1111-1111-111111111111`) | 相似案例参考 |
| CASE | 重复付款退款案 (`c6666666-6666-6666-6666-666666666666`) | 重复付款处理 |
| FAQ | 退款进度/未到账 FAQ | 退款时限说明 |

---

## 6. Draft Boundary

- 系统**只生成草稿**，不自动发送
- 草稿基于检索到的政策条款，不编造未检索到的信息
- 不承诺具体赔偿金额或时间
- 高风险场景在草稿顶部标注 ⚠️ 高风险，需人工审核
- 强制 `must_human_review = true`

---

## 7. What This Demo Proves

| 能力 | 说明 |
|------|------|
| 不只是 FAQ 问答 | 系统处理复合意图（退款+投诉+赔偿），不是简单 FAQ 匹配 |
| 风险识别深度 | 从自然语言中识别投诉、赔偿、法律三类风险标记 |
| 严重度自动升级 | 多个风险标记触发 HIGH severity |
| 高风险 → 人工审核 | 系统不自动处理高风险工单，强制路由到人工 |
| 证据驱动回复 | Draft 引用 Policy/Case 等证据，不凭空承诺 |
| 评估支撑 | Pipeline evaluation 验证 no_auto_send_compliance = 100% |

---

## 8. Limitations

- **Synthetic scenario**：本 demo 使用的人工编写示例工单，不是真实客服数据
- **Not real enterprise validation**：场景覆盖不代表真实业务分布
- **Fake embedding**：当前使用确定性 fake embedding（384-dim 哈希），仅验证管道机械正确性，不提供语义检索质量
- **Template draft**：草稿基于模板生成，不调用 LLM，不是生产级回复质量
- **Local demo only**：系统是本地作品集演示项目，不是生产部署
- **Phase 8 deferred**：真实 embedding provider 对比验证保留到 Phase 8

---

> **详见：** [phase7_demo_scenarios.md](phase7_demo_scenarios.md) | [Demo Guide](README.md) | [Sample Tickets](sample_tickets.md)
