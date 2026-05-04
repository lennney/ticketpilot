# Phase 7 Demo Scenarios Overview

> TicketPilot 的三个强 demo 场景总览，覆盖高风险投诉、隐私安全、支付发票三类典型客服场景。

---

## Scenario Comparison

| Dimension | Scenario 1: 退款投诉 | Scenario 2: 隐私/账号异常 | Scenario 3: 发票/支付争议 |
|-----------|---------------------|--------------------------|--------------------------|
| **File** | [scenario_refund_complaint.md](scenario_refund_complaint.md) | [scenario_privacy_account.md](scenario_privacy_account.md) | [scenario_invoice_payment.md](scenario_invoice_payment.md) |
| **Sample tickets** | 3 | 3 | 3 |
| **Issue type** | refund / complaint | account_issue | refund / other |
| **Risk flags** | complaint_risk, compensation_risk, legal_risk | account_security_risk, privacy_risk | policy_conflict, complaint_risk |
| **Severity** | HIGH | HIGH | LOW–MEDIUM |
| **must_human_review** | Always true | Always true | true when risk flags present |
| **Primary evidence** | Policy (赔偿/投诉/法律) + Case (律师函/重复付款) | Policy (隐私/安全) + Case (泄露/盗号) + FAQ | Policy (发票/支付) + Case (发票/重复付款) + FAQ |
| **Demo focus** | 多风险叠加 + 法律威胁 | 隐私安全 + 强制审核 | 政策对齐 + 条件审核 |

---

## Capability Coverage

| Capability | S1: 退款投诉 | S2: 隐私/账号 | S3: 发票/支付 |
|------------|:------------:|:-------------:|:-------------:|
| Intent classification | refund, complaint | account_issue | refund, other |
| Multi-intent detection | ✓ (退款+投诉+赔偿) | — | — |
| Risk flag detection | complaint, compensation, legal | account_security, privacy | policy_conflict, complaint |
| Severity escalation | ✓ (multiple flags → HIGH) | ✓ (security+privacy → HIGH) | — |
| Force human review | ✓ | ✓ | ✓ (true when risk flags present) |
| Evidence retrieval (FAQ/Policy/Case) | ✓ | ✓ | ✓ |
| Citation-grounded draft | ✓ | ✓ | ✓ |
| No unsupported promises | ✓ | ✓ | ✓ |
| Pipeline evaluation | ✓ (101 cases) | ✓ (101 cases) | ✓ (101 cases) |

---

## Interview Talking Points (3–5 Sentences Each)

### Scenario 1: 退款投诉

> "这个 demo 展示系统如何处理多意图叠加的高风险工单。当用户同时表达退款诉求、投诉不满和法律威胁时，系统能识别三类风险标记（投诉、赔偿、法律），自动将严重度升级为 HIGH，并强制路由到人工审核——系统不自动处理高风险场景。回复草稿基于检索到的赔偿政策和相似案例生成，不凭空承诺赔偿金额。这是 TicketPilot 风险识别能力最强的场景。"

### Scenario 2: 隐私/账号异常

> "这个 demo 展示系统对隐私安全类工单的敏感性。当用户报告异地登录或个人信息泄露时，系统能同时检测账号安全风险和隐私泄露风险，判定 HIGH severity 并强制人工审核。草稿回复基于隐私政策和安全流程生成，提供账号保护指引但不代用户执行敏感操作。这体现了系统在数据安全和个人信息保护方面的边界意识——知道什么时候应该交给人工处理。"

### Scenario 3: 发票/支付争议

> "这个 demo 展示系统在非高风险场景下的处理逻辑。支付扣款异常和纯发票咨询工单不需要每次都由人工处理——无风险标记时系统自动处理。但当工单包含 policy_conflict 或 complaint_risk 等风险标记时，系统自动触发人工审核。草稿基于发票政策和支付政策生成，与平台规则保持一致，不主动承诺退款或赔偿。这体现了系统的条件性判断能力：低风险自动处理，有风险标记时强制人工审核。"

---

## Screenshot Opportunities

| Screenshot | Scenario | What to Show |
|-----------|----------|--------------|
| Streamlit 工单输入 | All | 粘贴 Ticket A1/B1/C1 后点击"处理工单" |
| 风险评估区 | S1, S2 | 多个风险标记 + HIGH severity + must_human_review |
| Evidence candidates | S1 | Policy (赔偿/投诉) + Case (律师函) 的检索结果 |
| Draft reply with citations | All | 草稿引用具体政策条款和案例 |
| Human review controls | S1, S2 | Approve / Edit / Escalate / Reject 选项 |
| No high-risk auto-send | S1, S2 | 高风险草稿顶部的 ⚠️ 警告和不得自动发送提示 |
| Evaluation report | All | Pipeline evaluation 的 no_auto_send_compliance=100% |
| Quality gate | All | 终端显示 642 unit + 119 integration 0 skipped + 84% coverage |

---

## Workflow Summary

```
┌─────────────────────────────────────────────────────────────┐
│                  Ticket Intake (RawTicket)                    │
│  规范化原始文本，提取订单号、客户标识                        │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│              Intent Classification                           │
│  S1: refund / complaint    S2: account_issue    S3: refund  │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│              Risk Assessment                                 │
│  S1: complaint+compensation+legal → HIGH                    │
│  S2: account_security+privacy → HIGH                        │
│  S3: policy_conflict / none → LOW-MEDIUM                    │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│              Evidence Retrieval                              │
│  S1: Policy(赔偿/投诉/法律) + Case(律师函/重复付款)          │
│  S2: Policy(隐私/安全) + Case(泄露/盗号)                    │
│  S3: Policy(发票/支付) + Case(发票争议/重复付款)             │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│              Grounded Draft Reply                            │
│  基于证据生成草稿，附引用标注                                │
│  S1/S2: ⚠️ 高风险警告 + must_human_review                    │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌──────────────────────────────────────────────────────────────┐
│              Human Review                                    │
│  S1/S2: 强制审核 (Approve/Edit/Escalate/Reject)             │
│  S3: 仅在有投诉信号时审核                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## Related Documents

| Document | Link |
|----------|------|
| Demo Guide | [README.md](README.md) |
| Sample Tickets | [sample_tickets.md](sample_tickets.md) |
| Scenario 1: 退款投诉 | [scenario_refund_complaint.md](scenario_refund_complaint.md) |
| Scenario 2: 隐私/账号异常 | [scenario_privacy_account.md](scenario_privacy_account.md) |
| Scenario 3: 发票/支付争议 | [scenario_invoice_payment.md](scenario_invoice_payment.md) |
| Local Run Verification | [local_run_verification.md](local_run_verification.md) |

---

> **注意：** 所有 demo 场景均使用合成数据。系统为本地作品集演示项目，不反映生产级性能。
> 详见各场景文档中的 Limitations 部分。
