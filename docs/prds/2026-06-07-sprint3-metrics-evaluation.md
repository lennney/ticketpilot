# Sprint 3 PRD: 真实 Provider 延迟/成本 + Human Review 正确率

> PM: Hermes | Tech: Claude Code | Date: 2026-06-07
> 目标: 用真实数据替代 METRICS.md 中的 "not yet measured"

---

## 需求 1: 真实 Provider 延迟测量

### 背景

METRICS.md 中 "Real provider latency" 和 "Real provider estimated cost" 标记为 "not yet measured"。Phase 12 对比实验用了 deepseek-v4-pro，但没记录延迟和成本。

### 产品决策

测量 25 个 Phase 12 fixture 的真实 provider 延迟和成本，补充到 METRICS.md。

### 实现指引

- 文件: `scripts/measure_provider_latency.py`（新建）
- 复用 Phase 12 的 25 个 fixture case
- 对每个 case 计时 API 调用
- 记录: 每个 case 的延迟（秒）、token 数、估算成本

```python
import time
from ticketpilot.experiment.provider_comparison import load_phase12_fixtures
from ticketpilot.drafting.generator import DraftGenerator

def measure_latency():
    fixtures = load_phase12_fixtures()  # 25 个 case
    generator = DraftGenerator(provider="deepseek-v4-pro")

    results = []
    for fixture in fixtures:
        start = time.time()
        draft = generator.generate(fixture.evidence, fixture.risk_flags)
        elapsed = time.time() - start

        results.append({
            "ticket_id": fixture.ticket_id,
            "latency_s": round(elapsed, 2),
            "input_tokens": draft.input_tokens,
            "output_tokens": draft.output_tokens,
            "estimated_cost_usd": draft.estimated_cost,
        })

    # 汇总
    avg_latency = sum(r["latency_s"] for r in results) / len(results)
    total_cost = sum(r["estimated_cost_usd"] for r in results)
    print(f"Average latency: {avg_latency:.2f}s")
    print(f"Total cost (25 cases): ${total_cost:.4f}")
    print(f"Estimated cost per ticket: ${total_cost/len(results):.4f}")
```

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python scripts/measure_provider_latency.py 2>&1 | grep -E "latency|cost|ticket"
```

期望输出:
```
Average latency: X.XXs
Total cost (25 cases): $X.XXXX
Estimated cost per ticket: $X.XXXX
```

注意: 需要 `DEEPSEEK_API_KEY` 在 `.env.local` 中。如果没有 key，脚本应输出 "SKIPPED: no API key" 并 exit 0。

---

## 需求 2: Human Review 正确率评估

### 背景

Phase 13.10 中 48% (12/25) 的工单触发了人工审核。但没有测量：人工审核后，最终决策是否正确（该放行的放行了？该拦截的拦截了？）。

### 产品决策

创建一个评估框架：
1. 定义 "正确的人工审核决策" 的标准
2. 对 25 个 fixture 标注期望的审核结果
3. 模拟审核流程，验证系统是否正确标记了需要审核的工单

### 实现指引

- 文件: `tests/unit/test_human_review_accuracy.py`（新建）
- 定义评估标准:

```python
# 评估标准:
# - True Positive: 系统标记需要人工审核 + 确实需要审核（高风险/有法律威胁）
# - True Negative: 系统不标记 + 确实不需要审核（低风险/常规处理）
# - False Positive: 系统标记需要审核 + 实际不需要（过度保守）
# - False Negative: 系统不标记 + 实际需要审核（漏报，最严重）

REVIEW_EXPECTATIONS = {
    # ticket_id: expected_needs_review (True/False)
    "phase12_001": False,  # 普通退款
    "phase12_002": True,   # 法律威胁
    "phase12_003": False,  # 物流查询
    # ... 25 个 case 都标注
}
```

- 运行 Pipeline，对比实际触发 vs 期望
- 计算 precision, recall, F1

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python -m pytest tests/unit/test_human_review_accuracy.py -v --tb=short 2>&1 | tail -10
```

期望:
```
test_review_precision PASSED    # precision ≥ 0.8
test_review_recall PASSED       # recall ≥ 0.9 (宁可多审不能漏)
test_review_f1 PASSED           # F1 ≥ 0.85
test_no_false_negatives PASSED  # 高风险 case 不能漏
```

---

## 需求 3: 校准曲线真实数据训练

### 背景

IsotonicCalibrator 已实现，但一直用合成数据。Sprint 1 集成自反思后，Pipeline 会产生真实的 reflection 结果，可以用来训练校准器。

### 产品决策

用 Sprint 1 产出的 reflection 数据（passed/failed）作为反馈信号：
- reflection_passed=True → 原始置信度应该保持
- reflection_passed=False → 原始置信度偏高，需要校准

### 实现指引

- 文件: `scripts/calibrate_with_reflection.py`（新建）

```python
from ticketpilot.feedback.calibrator import IsotonicCalibrator
from ticketpilot.skills.loader import load_skill_library
from ticketpilot.skills.reflector import reflect_on_draft
from ticketpilot.classification.classifier import IntentClassifier

def collect_calibration_data():
    """从 eval tickets 收集校准数据"""
    classifier = IntentClassifier()
    library = load_skill_library()

    calibration_points = []  # (predicted_conf, actual_correct)

    # 对每张 eval ticket 运行 Pipeline + 反思
    for ticket in load_eval_tickets():
        classification = classifier.classify(ticket.text)
        # ... generate draft, reflect ...
        # reflection_passed = True/False
        # calibration_points.append((classification.confidence, reflection_passed))

    return calibration_points

def train_calibrator(points):
    calibrator = IsotonicCalibrator()
    calibrator.fit([p[0] for p in points], [p[1] for p in points])
    calibrator.save("data/calibration/isotonic_model.json")
    print(f"✅ 校准器训练完成: {len(points)} 个数据点")
```

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python scripts/calibrate_with_reflection.py 2>&1 | grep -E "✅|数据点|ECE"
```

期望:
```
✅ 校准器训练完成: XX 个数据点
校准前 ECE: X.XX
校准后 ECE: X.XX
```

校准后 ECE 应该 ≤ 校准前 ECE。

---

## 需求 4: 更新 METRICS.md

### 背景

Sprint 2 + Sprint 3 产生了新数据，需要更新 METRICS.md。

### 实现指引

在 METRICS.md 的 "Not-Yet-Measured Metrics" 表格中更新:

| Metric | 旧状态 | 新状态 |
|--------|--------|--------|
| Real provider latency | Not yet measured | **X.XXs avg** (Sprint 3) |
| Real provider estimated cost | Not yet measured | **$X.XXXX/ticket** (Sprint 3) |
| Human review trigger correctness | Not yet measured | **Precision X.XX, Recall X.XX** (Sprint 3) |
| Confidence distribution | Not yet measured | **See Dashboard** (Sprint 2) |

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && grep "not yet measured" docs/portfolio/METRICS.md | wc -l
```

期望: 比之前少（至少 2 个指标被更新）

---

## 全局验收 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate

# 1. 延迟测量（有 key 时）
python scripts/measure_provider_latency.py 2>&1 | tail -3

# 2. Human review 评估
python -m pytest tests/unit/test_human_review_accuracy.py -v --tb=short 2>&1 | tail -5

# 3. 校准器
python scripts/calibrate_with_reflection.py 2>&1 | tail -3

# 4. 全量测试
python -m pytest --tb=no -q 2>&1 | tail -3
```

期望:
- 延迟/成本数据就绪（或 SKIPPED）
- Human review 评估 PASSED
- 校准器训练完成
- 全量测试 1644+ passed, 0 failed

最后 commit:
```bash
git add -A && git commit -m "feat: provider latency measurement + human review evaluation + calibration"
```

---

## 约束

1. 没有 API key 时，延迟测量必须优雅降级（SKIPPED，不报错）
2. Human review 评估用合成数据（Phase 12 fixtures），不依赖真实审核
3. 校准器训练数据来自 Pipeline 运行结果，不造假
4. 所有现有测试继续通过
