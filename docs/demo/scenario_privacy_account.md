# Demo Scenario 2: 隐私/账号异常 (Account Issue + Privacy Risk)

> 账号安全和个人信息泄露是电商平台最敏感的风险场景之一。这个 demo 展示 TicketPilot 如何处理涉及账号异常、隐私泄露、安全风险的高敏感度工单。

---

## 1. Scenario Purpose

这个 Demo 展示 TicketPilot 在 **账号安全 + 隐私保护** 场景下的核心能力：

- **账号安全风险检测**：识别异地登录、账号被盗、异常订单等信号
- **隐私泄露风险检测**：识别个人信息泄露、骚扰电话、身份信息暴露
- **HIGH severity 判定**：安全+隐私双风险叠加升级
- **强制人工审核**：隐私相关场景自动 must_human_review
- **证据检索**：优先检索隐私政策、账号安全政策、相似案例
- **边界约束**：草稿不承诺赔偿，不自动执行账号操作

---

## 2. Example Tickets

### Ticket B1 — 异地登录 + 个人信息疑似泄露

```python
from ticketpilot.pipeline import intake_risk_pipeline
from ticketpilot.schema.ticket import RawTicket
from datetime import datetime

ticket = RawTicket(
    original_text="我的账号出现异地登录，而且手机号和实名信息好像被别人看到了，请马上处理。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_B1"
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

### Ticket B2 — 账号被盗 + 异常订单

```python
ticket = RawTicket(
    original_text="我的账号被人盗了，多了几笔不是我下的订单！密码也被改了。订单号：DEMO-ACCT-002。你们立刻冻结账号！",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_B2"
)
result = intake_risk_pipeline(ticket)

print(f"意图: {result.classification.intent.value}")
print(f"风险标记: {[f.value for f in result.risk_assessment.flags]}")
print(f"严重程度: {result.risk_assessment.severity.value}")
print(f"需人工审核: {result.risk_assessment.must_human_review}")
```

### Ticket B3 — 个人信息泄露导致骚扰电话

```python
ticket = RawTicket(
    original_text="自从在你们平台买了东西，天天收到诈骗电话，骗子连我买的什么都知道。肯定是你们泄露了我的信息，我要投诉！",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_B3"
)
result = intake_risk_pipeline(ticket)

print(f"意图: {result.classification.intent.value}")
print(f"风险标记: {[f.value for f in result.risk_assessment.flags]}")
```

---

## 3. Expected Workflow

```
Ticket Intake
  → 原始文本规范化，提取订单号 DEMO-ACCT-002
  → 客户标识 CUST_DEMO_Bx

Intent Classification
  → account_issue（账号问题）为主意图
  → "泄露""隐私""诈骗电话"等关键词触发 privacy 相关风险

Risk Assessment
  → ACCOUNT_SECURITY_RISK：异地登录、账号被盗
  → PRIVACY_RISK：个人信息泄露、骚扰电话
  → 双风险叠加 → severity 升级为 HIGH

Evidence Retrieval (Hybrid: Keyword + Vector)
  → 查询构建：账号 + 安全 + 隐私 + 泄露 + 冻结 + 密码
  → 融合检索：FAQ (账号恢复) + Policy (隐私政策) + Case (相似案例)

Draft Reply
  → 基于隐私政策和安全流程生成草稿
  → 附账号冻结/密码重置步骤说明
  → 标注隐私安全警告

Human Review
  → must_human_review = true
  → 审核员确认身份验证流程，核实后再执行账号操作
```

---

## 4. Expected Risk Behavior

| 字段 | Ticket B1 | Ticket B2 | Ticket B3 |
|------|-----------|-----------|-----------|
| `expected_issue_type` | account_issue | account_issue | account_issue / complaint |
| `risk_flags` | account_security_risk, privacy_risk | account_security_risk | privacy_risk, complaint_risk |
| `severity` | HIGH | HIGH | HIGH |
| `must_human_review` | true | true | true |
| `fallback_required` | false | false | false |
| `no_auto_send` | true | true | true |

---

## 5. Expected Evidence Behavior

应优先检索的证据类型和代表性文档：

| Doc Type | Content | Supports |
|----------|---------|----------|
| POLICY | 隐私泄露升级处理规则 (`ad0d0d0d-6666-6666-6666-666666666666`) | 隐私事件处理流程 |
| POLICY | 账号安全事件处理规则 | 账号冻结/解冻流程 |
| CASE | 个人信息泄露案 (`c4444444-4444-4444-4444-444444444444`) | 相似案例处理结果 |
| CASE | 账号异地登录案 (`c5555555-5555-5555-5555-555555555555`) | 账号安全案例 |
| CASE | 账号被盗案 (`b4444444-4444-4444-4444-444444444444`) | 账号盗用处理 |
| FAQ | 账号安全 FAQ（如何修改密码/开启二次验证） | 用户操作指引 |

---

## 6. Draft Boundary

- 系统**只生成草稿**，不自动发送
- 草稿包含隐私安全提示，不代用户执行账号冻结/密码重置
- 不承诺赔偿或补偿金额
- 建议用户主动开启二次验证，但不代替用户操作
- 强制 `must_human_review = true`

---

## 7. What This Demo Proves

| 能力 | 说明 |
|------|------|
| 隐私风险检测 | 从"泄露""诈骗电话""异地登录"等自然语言信号识别 privacy_risk |
| 账号安全检测 | 从"被盗""改密码""异常订单"等信号识别 account_security_risk |
| 安全敏感度 | 安全类场景自动 HIGH severity，不降级处理 |
| 隐私保护边界 | 草稿不要求用户提供明文密码，不代替用户执行敏感操作 |
| 证据检索多样性 | 同时检索隐私政策、安全流程、相似案例三种证据类型 |
| 人工审核强制 | 隐私/安全类工单即使内容简短也强制人工审核 |

---

## 8. Limitations

- **Synthetic scenario**：本 demo 使用的人工编写示例工单，不是真实客服数据
- **Not real enterprise validation**：场景覆盖不代表真实业务分布
- **Fake embedding**：当前使用确定性 fake embedding（384-dim 哈希），仅验证管道机械正确性，不提供语义检索质量
- **Template draft**：草稿基于模板生成，不调用 LLM，不是生产级回复质量
- **Local demo only**：系统是本地作品集演示项目，不是生产部署
- **Phase 8 deferred**：真实 embedding provider 对比验证保留到 Phase 8
- **No real auth**：系统不包含真实用户认证或账号操作能力

---

> **详见：** [phase7_demo_scenarios.md](phase7_demo_scenarios.md) | [Demo Guide](README.md) | [Sample Tickets](sample_tickets.md)
