# 设计文档：草稿质量门禁 — 自动发送的双重判断

> **文档类型：** 产品设计 + 技术方案
> **状态：** 草案
> **日期：** 2026-06-10

---

## 1. 问题定义

### 当前行为

TicketPilot 的路由逻辑只看**置信度分数**：

```
置信度 HIGH (>0.78)  → 自动发送
置信度 MEDIUM (0.6-0.78) → 自动发送 + 免责声明
置信度 LOW (0.4-0.6) → 人工审核
置信度 CRITICAL (<0.4) → 升级到人工
```

### 问题

**一个置信度 HIGH 的工单，草稿可能有严重质量问题：**

| 场景 | 置信度 | 草稿质量 | 当前行为 | 正确行为 |
|------|--------|---------|---------|---------|
| 客户问退款政策，草稿引用了正确 Policy | HIGH | ✅ 好 | 自动发送 | 自动发送 |
| 客户问退款政策，草稿承诺"3 天内到账"（禁止承诺） | HIGH | ❌ 坏 | **自动发送** | 人工审核 |
| 客户投诉，草稿有引用但覆盖不全 | MEDIUM | ⚠️ 一般 | 自动发送+免责 | 人工审核 |
| 客户威胁投诉，草稿未引用 Case 文档 | HIGH | ❌ 坏 | **自动发送** | 人工审核 |

### 业务影响

| 影响 | 描述 |
|------|------|
| **客户体验** | 发出错误回复比不回复更糟——客户会截图投诉 |
| **法律风险** | 承诺退款金额、泄露隐私等可能引发法律问题 |
| **信任损失** | 一次错误回复可能让客户永远离开 |
| **成本反转** | 自动发送错误回复 → 客户投诉 → 人工处理 → 比一开始就人工审核更贵 |

### 核心洞察

> 自动发送的门槛不应该是"系统有多确定"（置信度），而是"系统有多确定 + 回复有多安全"（置信度 × 质量）。
>
> **置信度回答的是"我知不知道该说什么"，质量回答的是"我说的对不对、安全不安全"。**

---

## 2. 设计方案

### 2.1 双重门禁模型

```
┌──────────────────────────────────────────────────────┐
│                   路由决策树（改进后）                    │
│                                                       │
│  置信度评分                                            │
│      │                                                │
│      ├── CRITICAL → 人工升级（不生成草稿）              │
│      │                                                │
│      ├── LOW → 人工审核                                │
│      │                                                │
│      ├── MEDIUM ──→ 草稿质量检查 ──┐                   │
│      │                            ├── 通过 → 自动发送+免责│
│      │                            └── 不通过 → 人工审核  │
│      │                                                │
│      └── HIGH ───→ 草稿质量检查 ──┐                    │
│                                   ├── 通过 → 自动发送   │
│                                   └── 不通过 → 人工审核  │
└──────────────────────────────────────────────────────┘
```

### 2.2 草稿质量检查维度

| 检查项 | 来源 | 失败时行为 | 说明 |
|--------|------|-----------|------|
| **禁止承诺检测** | guardrails | → 人工审核 | 退款金额、法律威胁、隐私承诺等 8 类 |
| **引用完整性** | drafting | → 人工审核 | 所有声明必须有 citations 支撑 |
| **Guard 通过** | drafting | → 人工审核 | claim_guard 检查未通过 |
| **证据覆盖** | retrieval | → 人工审核 | evidence_doc_types 覆盖不足 |

### 2.3 质量分数计算

```python
def compute_draft_quality_score(
    guardrail_passed: bool,
    citation_precision: float,    # 0-1
    claim_guard_passed: bool,
    evidence_coverage: float,     # 0-1
) -> tuple[float, list[str]]:
    """计算草稿质量分 (0-1) 和失败原因列表。"""
    score = 0.0
    failures = []

    # 禁止承诺：一票否决
    if not guardrail_passed:
        failures.append("forbidden_promise")

    # 引用完整性
    if citation_precision >= 0.8:
        score += 0.3
    elif citation_precision >= 0.5:
        score += 0.15
    else:
        failures.append(f"low_citation({citation_precision:.0%})")

    # Guard 通过
    if claim_guard_passed:
        score += 0.3
    else:
        failures.append("claim_guard_failed")

    # 证据覆盖
    if evidence_coverage >= 0.7:
        score += 0.4
    elif evidence_coverage >= 0.4:
        score += 0.2
    else:
        failures.append(f"low_evidence({evidence_coverage:.0%})")

    # 禁止承诺一票否决
    if "forbidden_promise" in failures:
        score = 0.0

    return score, failures


# 自动发送阈值
QUALITY_THRESHOLD_AUTO_SEND = 0.7       # ≥ 0.7 才允许自动发送
QUALITY_THRESHOLD_AUTO_SEND_CAUTIOUS = 0.5  # ≥ 0.5 才允许谨慎自动发送
```

### 2.4 路由逻辑（伪代码）

```python
def route(confidence, draft_quality_score, draft_quality_failures):
    # CRITICAL: 无条件升级
    if confidence.level == CRITICAL:
        return HUMAN_ESCALATION

    # LOW: 无条件人工审核
    if confidence.level == LOW:
        return HUMAN_REVIEW

    # HIGH: 看质量
    if confidence.level == HIGH:
        if draft_quality_score >= 0.7:
            return AUTO_SEND
        else:
            return HUMAN_REVIEW  # 置信度高但质量不够

    # MEDIUM: 看质量（阈值更低）
    if confidence.level == MEDIUM:
        if draft_quality_score >= 0.5:
            return AUTO_SEND_CAUTIOUS
        else:
            return HUMAN_REVIEW
```

---

## 3. 指标体系

### 3.1 核心业务指标

| 指标 | 公式 | 含义 | 当前值 | 目标 |
|------|------|------|--------|------|
| **自动化率** | auto_sent / total | 多少工单自动处理 | ~60% | 50-70%（质量优先） |
| **错误发送率** | errors / auto_sent | 自动发送中有多少出错 | 未知（未追踪） | < 2% |
| **人工审核率** | human_review / total | 多少工单需要人工 | ~40% | 30-50% |
| **升级率** | escalation / total | 多少工单升级到高级人工 | ~5% | < 10% |

### 3.2 质量指标

| 指标 | 公式 | 含义 |
|------|------|------|
| **质量通过率** | quality_passed / auto_eligible | 置信度够但质量也够的比例 |
| **质量拦截率** | quality_blocked / high_confidence | HIGH 置信度但被质量拦截的比例 |
| **禁止承诺检出率** | forbidden_caught / forbidden_total | 禁止承诺被正确拦截的比例 |

### 3.3 效率指标

| 指标 | 公式 | 含义 |
|------|------|------|
| **人工节省比** | 1 - (human_review + escalation) / total | 节省了多少人工 |
| **平均处理时间** | avg(end_to_end_time) | 从工单到回复的平均时间 |
| **首次解决率** | first_contact_resolved / auto_sent | 自动发送后客户是否满意 |

---

## 4. 对现有系统的影响

### 4.1 需要修改的模块

| 模块 | 改动 | 影响范围 |
|------|------|---------|
| `degradation/router.py` | `route()` 接受 `draft_quality` 参数 | 核心路由逻辑 |
| `confidence/scorer.py` | 无改动 | 不变 |
| `drafting/` | 无改动 | 草稿生成不变 |
| `guardrails/` | 无改动 | 检查结果被路由使用 |
| `evaluation/metrics.py` | 新增 `quality_gate_accuracy` 指标 | 评测管线 |
| `review/console.py` | 显示质量检查结果 | 人工审核台 |

### 4.2 向后兼容

- `route()` 的 `draft_quality` 参数可选，默认 `None`（向后兼容）
- 无质量数据时，退化为当前行为（只看置信度）
- 评测管线新增 `quality_gate_accuracy` 指标，不影响现有指标

### 4.3 数据流变化

```
当前:
  ticket → classify → risk → retrieve → draft → confidence → route → send/review

改进后:
  ticket → classify → risk → retrieve → draft → confidence ─┐
                                                             ├→ route → send/review
                                              draft_quality ─┘
                                              (guardrails + citations + evidence)
```

---

## 5. 实现路径

### Phase 1：质量评分模块（1-2 天）

**目标：** 创建 `DraftQualityScorer`，独立于路由

- 创建 `ticketpilot/quality/scorer.py`
- 实现 `compute_draft_quality_score()`
- 实现 4 个子检查函数
- 单元测试（TDD）

### Phase 2：路由集成（1 天）

**目标：** 路由器接受质量分数并应用双重判断

- 修改 `DegradationRouter.route()` 签名
- 实现双重门禁逻辑
- 向后兼容（quality=None 时退化）
- 单元测试

### Phase 3：评测集成（1 天）

**目标：** 评测管线追踪质量门禁效果

- 新增 `quality_gate_accuracy` 指标
- 新增 `quality_intercept_rate` 指标
- 更新 `EvaluationSummary`
- 用现有 101 条评测数据验证

### Phase 4：审核台增强（0.5 天）

**目标：** 人工审核台显示质量检查结果

- 在 Streamlit 审核台显示质量分数
- 显示失败原因（哪些检查没通过）
- 显示"如果质量通过，这个工单会自动发送"

---

## 6. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 质量阈值设太高 | 自动化率大幅下降 | 从 0.7 开始，根据数据调整 |
| 质量阈值设太低 | 错误发送仍然发生 | 禁止承诺一票否决，不可调 |
| 质量检查误报 | 好草稿被拦截 | 降低 recall 要求，宁可漏不可错 |
| 与置信度权重冲突 | 两个系统打架 | 质量是"否决权"，不是"加分项" |

---

## 7. 成本效益分析

### 假设条件

- 日均 1000 条工单
- 人工审核成本：¥5/条（客服 10 分钟 × ¥30/小时）
- 错误发送成本：¥50/条（投诉处理 + 客户流失）

### 当前模式（纯置信度）

```
自动发送 600 条 × ¥0 = ¥0（但假设 5% 出错 = 30 条 × ¥50 = ¥1,500 损失）
人工审核 400 条 × ¥5 = ¥2,000
总成本：¥3,500/天
```

### 改进模式（双重门禁）

```
自动发送 500 条 × ¥0 = ¥0（错误率 < 1% = 5 条 × ¥50 = ¥250 损失）
人工审核 500 条 × ¥5 = ¥2,500
总成本：¥2,750/天
```

### 节省

```
每天节省 ¥750（21%）
每月节省 ¥22,500
每年节省 ¥270,000
```

**关键洞察：** 减少 100 条自动发送（从 600→500），但减少 25 条错误发送（从 30→5），净节省 ¥750/天。

---

## 8. 成功标准

| 指标 | 基线（当前） | Phase 1 目标 | Phase 2 目标 |
|------|------------|-------------|-------------|
| 错误发送率 | ~5%（估算） | < 2% | < 1% |
| 自动化率 | ~60% | ~50% | ~55%（质量提升后可放宽） |
| 禁止承诺拦截率 | 0%（未追踪） | 100% | 100% |
| 人工节省比 | ~60% | ~50% | ~55% |

---

## 附录：与 CrawlWeaver 的方法论对比

| 维度 | CrawlWeaver | TicketPilot |
|------|-------------|-------------|
| 质量门禁 | AI 评分 + 规则检查 | 置信度 + 草稿质量 |
| 自愈机制 | 验证失败 → 重写 | 质量不通过 → 人工审核 |
| 知识进化 | TLD 共享 + 衰减 | 评测驱动优化 |
| 核心指标 | 通过率、成本、覆盖率 | 自动化率、错误率、审核率 |

**共同原则：** 用确定性规则兜底 AI 的不确定性。AI 负责生成，规则负责安全。
