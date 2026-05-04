# Phase 7 MVP Evidence Pack — Portfolio Snapshot

> **One-liner:** Expanded TicketPilot's evaluation dataset from 10 to 101 tickets and knowledge base from 36 to 95 records, built 3 strong demo scenarios, and established a deterministic offline evaluation pipeline — all with synthetic data, fake embeddings, and zero LLM calls.

---

## Before → After

| Metric | Before | After | Delta |
|--------|------:|-----:|:-----:|
| Eval tickets | 10 | **101** | +91 |
| Golden expectations | 10 | **101** | +91 |
| Sample predictions | 10 | **101** | +91 |
| Intent classes covered | 8 | 8 (depth expanded) | — |
| Risk flag types | 5 | **8** | +3 |
| Severity levels | 3 | 3 (balanced distribution) | — |
| Multi-intent tickets | 0 | **7** | +7 |
| Edge case tickets | 0 | **5** | +5 |
| Invoice/payment domain | 0 | **9** | +9 |
| **Knowledge records** | **36** | **95** | +59 |
| FAQ | 12 | **40** | +28 |
| Policy | 12 | **30** | +18 |
| Case | 12 | **25** | +13 |
| Knowledge chunks | 36 | **95** | +59 |
| Business domains covered | 5 | **8** (all) | +3 |
| Demo scenarios | 0 | **3** | +3 |
| OpenSpec specs | — | 4 new (data, evaluation, demo, knowledge-base) | +4 |
| Limitations doc | — | **1** (9 sections) | +1 |
| Pipeline reports | 2 (10 tickets) | 4 (101 tickets) | +2 |
| Quality gate tests | — | 642 unit / 119 integration (0 skipped) | — |

---

## Three Strong Demo Scenarios

### Scenario 1: 退款投诉 (Refund + Complaint)
- **Risk flags:** complaint_risk, compensation_risk, legal_risk
- **Severity:** HIGH
- **must_human_review:** Always true
- **Evidence:** Policy (compensation rules, complaint escalation, legal threat) + Case (lawyer letter, duplicate payment)
- **What it proves:** Multi-intent detection, compound risk flag escalation, forced human review for high-risk tickets

### Scenario 2: 隐私/账号异常 (Account Issue + Privacy Risk)
- **Risk flags:** account_security_risk, privacy_risk
- **Severity:** HIGH
- **must_human_review:** Always true
- **Evidence:** Policy (privacy leak, account security) + Case (info leak, account theft) + FAQ
- **What it proves:** Privacy-sensitive risk detection, security boundary awareness, evidence-driven draft without executing sensitive operations

### Scenario 3: 发票/支付争议 (Invoice + Payment Dispute)
- **Risk flags:** policy_conflict, complaint_risk (conditional)
- **Severity:** LOW–MEDIUM
- **must_human_review:** True when risk flags present; false for no-risk inquiries
- **Evidence:** Policy (invoice rules, payment handling) + Case (invoice dispute, duplicate payment) + FAQ
- **What it proves:** Conditional human review, domain-specific evidence retrieval, policy-aligned drafts without unsupported promises

---

## Evaluation System

| Mode | Description |
|------|-------------|
| **CSV evaluation** | Loads `sample_predictions.csv` for deterministic offline scoring |
| **Pipeline evaluation** | Runs full pipeline (intake → classify → assess → retrieve → draft) for each of 101 tickets |
| **No-auto-send compliance** | 100% — architecture constraint, not a model metric |
| **Intent accuracy** | 53.5% (pipeline mode, reflects fake embedding + rule components) |
| **Severity accuracy** | 54.5% (pipeline mode) |
| **Risk flag F1** | 29.8% (pipeline mode) |
| **Evidence doc type recall** | 43.2% (pipeline mode) |
| **Fallback correctness** | 90.1% (pipeline mode) |

**Note:** Pipeline mode metrics reflect deterministic behavior of fake embeddings and rule-based components. They validate that the evaluation framework works end-to-end, not production-level performance.

---

## Project Boundaries

| Constraint | Detail |
|-----------|--------|
| **Maturity** | Local demo / portfolio prototype, not production |
| **Data** | 100% synthetic / manually adapted — no real enterprise data |
| **Embedding** | FakeEmbeddingProvider (384-dim deterministic SHA-256 hash) — only validates pipeline mechanics |
| **LLM** | Zero — all drafts use template generation (FakeDraftProvider) |
| **Auto-send** | No — architectural constraint. All output is draft-only, no send channel exists |
| **Evaluation** | Offline deterministic, not online A/B test or real business benchmark |
| **Storage** | Local PostgreSQL + pgvector via Docker Compose |
| **Auth** | None — single-user Streamlit console |

---

## Resume Bullets (Chinese)

> **Senior AI Engineer — TicketPilot: MVP Evidence Pack (Phase 7)**
>
> - 将评测数据集从 10 条扩展到 101 条合成中文客服工单，覆盖 8 类意图、8 种风险标记、3 级严重度，新增发票/支付领域和多意图工单
> - 将知识库从 36 条扩展到 95 条记录（FAQ=40, Policy=30, Case=25），覆盖所有业务领域和 10 个评测场景
> - 设计并实现了 3 个强 demo 场景文档（退款投诉、隐私/账号异常、发票/支付争议），包含示例工单、预期流程、风险行为和限制说明
> - 建立了确定性离线评测流水线，支持 CSV 预测模式和完整 Pipeline 预测模式，7 项指标覆盖意图、风险、证据、人工审核
> - 确保 system boundary：不使用真实企业数据、不使用 LLM、不自动发送回复，fake embedding 仅验证管道机械正确性
> - 质量门禁：642 单元测试 + 119 集成测试（0 skip）+ 84% 覆盖率 + OpenSpec 16/16

---

## Interview Talking Points

### 1-Minute Version

> "Phase 7 的核心成果是把 TicketPilot 从一个 10 条数据的 demo 原型，扩展成了一个有 101 条评测工单、95 条知识记录的、可演示、可评估、有边界约束的产品原型。我扩了知识库结构——FAQ、Policy、Case 三种类型——加了发票、支付、隐私安全等新领域，建了 3 个强 demo 场景。同时所有数据都是合成/改编的，不用 LLM，不自动发送，fake embedding 只验证管道。这更像一个架构演示——证明了一个可评测、可追溯、安全约束明确的客服工单处理系统如何搭建。"

### 3-Minute Version

> "Phase 7 的目标是把 TicketPilot 从一个功能原型升级为一个可说清规模、可演示、有评测数据支撑的产品原型。
>
> **数据规模方面**，我把评测数据集从 10 条工单扩展到 101 条，覆盖了所有 8 类意图（退款、换货、账号、投诉、物流、技术、咨询、其他），8 种风险标记（投诉、赔偿、法律、账号安全、隐私、政策冲突、低置信度、证据不足），新增了发票/支付领域，以及 7 条多意图组合工单。知识库从 36 条扩展到 95 条，FAQ、Policy、Case 三种文档类型都补齐了，覆盖 10 个评测场景。
>
> **Demo 方面**，我做了 3 个强场景文档。第一个是退款投诉，能展示多个风险标记叠加后自动升级 HIGH severity 并强制人工审核。第二个是隐私/账号异常，展示系统对安全类场景的敏感性和边界意识。第三个是发票/支付争议，展示条件性人工审核——低风险自动处理，有风险信号时再触发审核。
>
> **项目约束方面**，所有数据都是合成或根据公开信息改编的，没有使用任何真实企业数据。嵌入使用确定性 fake embedding，不调用 LLM，所有输出都是草稿不自动发送。评测流水线支持 CSV 和 Pipeline 两种模式，no-auto-send compliance = 100% 是架构约束。
>
> **Phase 8 规划**是替换 fake embedding 为真实中文嵌入服务（text2vec/BGE），做检索质量评估对比。但在这之前，Phase 7 已为项目建立了完整的数据基底、评测体系和 demo 素材。"

---

## Next Step: Phase 8 Roadmap

| Direction | Priority | Dependency |
|-----------|----------|------------|
| Real Chinese embedding provider (text2vec / BGE) | High | Phase 7 completion |
| Retrieval quality evaluation (precision/recall/NDCG) | High | Real embeddings |
| Real LLM draft generation (optional, switchable) | Medium | Embedding eval |
| Expanded eval dataset (200+ tickets) | Medium | Data collection |
| Online / regression evaluation | Low | Core metrics stable |

**Phase 8 will not start until Phase 7 is fully archived and the embedding provider integration is designed as an OpenSpec change.**

---

> *Part of the [TicketPilot](https://github.com/lennney/ticketpilot) portfolio project. See [changelog](../../docs/changelog.md) for full history.*
