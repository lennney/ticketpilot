# Sample Tickets for Demo

> Copy-pasteable ticket inputs for each demo scenario.
> All tickets include `submitted_at` and `customer_id` fields.

---

## 1. 普通退款工单 (Refund)

**场景：** 客户因商品质量问题申请退款。

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

print(f"意图: {result.classification.intent.value}")
print(f"严重程度: {result.risk_assessment.severity.value}")
print(f"风险标记: {[f.value for f in result.risk_assessment.flags]}")
print(f"需人工审核: {result.risk_assessment.must_human_review}")
```

| 字段 | 预期值 |
|------|--------|
| `intent` | `refund` |
| `severity` | `low` |
| `flags` | `[]` (无风险标记) |
| `must_human_review` | `False` |

**观察要点：** 单一意图、无风险标记、低严重程度。证据候选项应包含 FAQ 类型文档。

---

## 2. 退换货工单 (Return / Exchange)

**场景：** 客户因尺码不合适要求换货。

```python
ticket = RawTicket(
    original_text="我想退货换货，订单号：654321，尺码不合适。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_002"
)
result = intake_risk_pipeline(ticket)

print(f"意图: {result.classification.intent.value}")
print(f"严重程度: {result.risk_assessment.severity.value}")
```

| 字段 | 预期值 |
|------|--------|
| `intent` | `return_exchange` |
| `severity` | `low` |
| `flags` | `[]` |

**观察要点：** 与退款工单的 `intent` 不同，展示意图分类的区分能力。同样无风险标记。

---

## 3. 物流查询工单 (Logistics)

**场景：** 客户查询物流状态。

```python
ticket = RawTicket(
    original_text="我的快递怎么还没到？订单号：789012，已经五天了。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_006"
)
result = intake_risk_pipeline(ticket)

print(f"意图: {result.classification.intent.value}")
print(f"严重程度: {result.risk_assessment.severity.value}")
```

| 字段 | 预期值 |
|------|--------|
| `intent` | `logistics` |
| `severity` | `low` |
| `flags` | `[]` |

**观察要点：** 物流类工单被正确分类，低风险。

---

## 4. 账号问题工单 (Account Issue)

**场景：** 客户反馈账号被冻结。

```python
ticket = RawTicket(
    original_text="我的账号被冻结了，无法登录，请帮我解封。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_007"
)
result = intake_risk_pipeline(ticket)

print(f"意图: {result.classification.intent.value}")
print(f"风险标记: {[f.value for f in result.risk_assessment.flags]}")
```

| 字段 | 预期值 |
|------|--------|
| `intent` | `account_issue` |
| `severity` | `medium` |
| `flags` | `[]` 或 `account_security_risk` |

**观察要点：** 账号相关问题可能触发安全风险标记。

---

## 5. 高风险投诉 + 赔偿 + 法律威胁 (Complaint)

**场景：** 客户强烈投诉并要求赔偿，附带法律威胁。

```python
ticket = RawTicket(
    original_text="客服态度太差了，我要投诉！要求3倍赔偿，不然我就找律师起诉你们。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_003"
)
result = intake_risk_pipeline(ticket)

print("=== 意图分类 ===")
print(f"意图: {result.classification.intent.value}")

print("\n=== 风险评估 ===")
print(f"严重程度: {result.risk_assessment.severity.value}")
print(f"风险标记: {[f.value for f in result.risk_assessment.flags]}")
print(f"需人工审核: {result.risk_assessment.must_human_review}")
```

| 字段 | 预期值 |
|------|--------|
| `intent` | `complaint` |
| `severity` | `high` |
| `flags` | `complaint_risk`, `compensation_risk`, `legal_risk` |
| `must_human_review` | `True` |

**观察要点：** 多个风险标记叠加，严重程度升级为 `high`。系统强制人工审核。在 Streamlit 控制台中应显示 Escalate 或 Reject 选项。

---

## 6. 隐私 / 账号安全高风险 (Privacy / Account Security)

**场景：** 客户反馈个人信息泄露风险。

```python
ticket = RawTicket(
    original_text="我的账号被冻结了，个人信息可能泄露了，手机号被他人使用。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_004"
)
result = intake_risk_pipeline(ticket)

print(f"意图: {result.classification.intent.value}")
print(f"风险标记: {[f.value for f in result.risk_assessment.flags]}")
print(f"需人工审核: {result.risk_assessment.must_human_review}")
```

| 字段 | 预期值 |
|------|--------|
| `intent` | `account_issue` |
| `severity` | `high` |
| `flags` | `account_security_risk`, `privacy_risk` |
| `must_human_review` | `True` |

**观察要点：** 隐私相关风险触发强制人工审核。多个风险标记叠加。

---

## 7. 弱证据 / 简短输入 (Weak Evidence)

**场景：** 客户只输入了极短的文本。

```python
ticket = RawTicket(
    original_text="退款。",
    submitted_at=datetime.utcnow(),
    customer_id="CUST_DEMO_005"
)
result = intake_risk_pipeline(ticket)

print(f"意图: {result.classification.intent.value}")
print(f"风险标记: {[f.value for f in result.risk_assessment.flags]}")
print(f"需人工审核: {result.risk_assessment.must_human_review}")
print(f"证据数: {len(result.evidence_candidates)}")
```

| 字段 | 预期值 |
|------|--------|
| `intent` | `refund` |
| `flags` | 可能包含 `insufficient_evidence` |
| `must_human_review` | 视证据数量而定 |

**观察要点：** 即使只有"退款。"两字，意图分类仍能正确识别。但可能触发 `insufficient_evidence` 标记。如果开启了草稿生成，应展示 fallback 回复而非编造信息。

---

## 快速参考表

| # | 场景 | Intent | Severity | 风险标记 | 需审核 |
|---|------|--------|----------|----------|--------|
| 1 | 退款-质量问题 | `refund` | `low` | 无 | 否 |
| 2 | 退换货-尺码 | `return_exchange` | `low` | 无 | 否 |
| 3 | 物流查询 | `logistics` | `low` | 无 | 否 |
| 4 | 账号冻结 | `account_issue` | `medium` | `account_security_risk` | 可能 |
| 5 | 投诉+赔偿+法律 | `complaint` | `high` | 3 个风险标记 | **是** |
| 6 | 隐私泄露 | `account_issue` | `high` | `privacy_risk` | **是** |
| 7 | 仅"退款"二字 | `refund` | `low` | `insufficient_evidence` | 可能 |

---

> **注意：** 预期值基于种子数据和确定性规则。如果实际输出与预期不符，请检查数据库是否正确初始化（`alembic upgrade head && uv run python scripts/ingest_knowledge.py`）。
>
> 所有演示结果均基于本地确定性逻辑，不反映真实世界性能。
