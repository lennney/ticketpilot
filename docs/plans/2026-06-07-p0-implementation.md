# P0 实现计划：Multi-Agent 真实化 + Feedback Loop

> 2026-06-07

---

## Task 1: Multi-Agent 真实化（2-3h）

### 问题
5 个 Specialist 全部调同一个 `DraftAgent.generate_draft()`，没有差异化。

### 改动

#### 1.1 为每个 Agent 定制 Prompt Template
- 文件：`src/ticketpilot/drafting/prompt_builder.py`
- 当前：单一 prompt template
- 改为：按 intent 选择不同 template

```python
# prompts/templates/complaint.md — 情绪安抚 + 强制人工
# prompts/templates/refund.md — 退款流程引导
# prompts/templates/logistics.md — 物流状态查询
# prompts/templates/technical.md — 故障排查步骤
# prompts/templates/default.md — 通用回复
```

#### 1.2 为每个 Agent 定制 Guard 规则
- 文件：`src/ticketpilot/drafting/claim_guard.py`
- ComplaintAgent：额外检查情绪安抚语句是否存在
- RefundAgent：额外检查退款政策引用
- LogisticsAgent：额外检查物流单号格式
- TechnicalAgent：额外检查故障排查步骤

#### 1.3 更新 Multi-Agent Orchestrator
- 文件：`src/ticketpilot/multi_agent/__init__.py`
- 每个 Agent 传入对应的 prompt_template_id
- DraftAgent 根据 template_id 选择 prompt

#### 1.4 测试
- 文件：`tests/unit/test_multi_agent.py`（新建）
- 测试每个 Agent 使用不同的 prompt template
- 测试 ComplaintAgent 强制 must_human_review
- 测试 Orchestrator 路由正确性

---

## Task 2: Feedback Loop（3-4h）

### 问题
人工审后 accept/reject/edit 结果没有回流。置信度阈值是静态的。

### 改动

#### 2.1 FeedbackCollector
- 文件：`src/ticketpilot/feedback/collector.py`（新建）
- 从 ReviewDecision 收集 (confidence, action, was_correct) 三元组
- 持久化到 feedback.jsonl

```python
@dataclass
class FeedbackRecord:
    ticket_id: str
    predicted_confidence: float
    confidence_level: str  # HIGH/MEDIUM/LOW/CRITICAL
    review_action: str  # accept/reject/edit/escalate
    was_correct: bool  # accept=True, reject=False, edit=partial
    original_draft: str
    edited_draft: str | None
    timestamp: datetime
```

#### 2.2 CalibrationCurve
- 文件：`src/ticketpilot/feedback/calibrator.py`（新建）
- 按置信度分桶（0-0.2, 0.2-0.4, 0.4-0.6, 0.6-0.8, 0.8-1.0）
- 计算每个桶的 actual accuracy
- 输出 reliability data

```python
@dataclass
class CalibrationBucket:
    predicted_range: tuple[float, float]
    count: int
    actual_accuracy: float
    avg_predicted_confidence: float

class CalibrationCurve:
    buckets: list[CalibrationBucket]
    
    def suggest_threshold(self, target_accuracy: float) -> float:
        """找到满足 target_accuracy 的最低置信度阈值"""
```

#### 2.3 阈值建议器
- 文件：`src/ticketpilot/feedback/threshold_advisor.py`（新建）
- 基于 CalibrationCurve 建议新阈值
- 不自动修改，输出建议供人工确认

#### 2.4 集成到 Review Console
- 文件：`src/ticketpilot/review/console.py`
- 审后记录 FeedbackRecord
- 新 Streamlit 页面展示 CalibrationCurve

#### 2.5 测试
- 文件：`tests/unit/test_feedback.py`（新建）
- 测试 FeedbackCollector 记录正确
- 测试 CalibrationCurve 分桶计算
- 测试 ThresholdAdvisor 建议逻辑

---

## 执行顺序

```
1. Task 1.1 — Prompt templates（每个 Agent 一个 .md 文件）
2. Task 1.2 — Guard 规则定制
3. Task 1.3 — Orchestrator 更新
4. Task 1.4 — Multi-Agent 测试
5. Task 2.1 — FeedbackCollector
6. Task 2.2 — CalibrationCurve
7. Task 2.3 — ThresholdAdvisor
8. Task 2.4 — Review Console 集成
9. Task 2.5 — Feedback 测试
10. 全量测试验证
```

## 验收标准

- [ ] 5 个 Agent 使用不同 prompt template
- [ ] ComplaintAgent 强制 must_human_review
- [ ] 人工审后自动记录 FeedbackRecord
- [ ] CalibrationCurve 能正确分桶计算
- [ ] ThresholdAdvisor 能输出阈值建议
- [ ] 全量测试 1356+ 通过
