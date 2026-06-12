# TicketPilot 自迭代优化系统设计

> 日期: 2026-06-10
> 状态: 设计完成（已审查）
> 触发: 用户手动执行 `python -m ticketpilot.optimizer --rounds 20`

## 一、设计目标

**一句话**: 手动触发一次，系统自动跑 20 轮「评测→诊断→修复→验证→提交」，每轮都有分数变化记录，最终输出完整报告。

**核心价值**:
1. **防退步** — 每次改代码后自动验证 101 条工单没退步
2. **可追踪** — 每轮改了什么、效果如何，全部记录
3. **可复现** — 每次修复独立 Git commit，可随时 revert
4. **作品集** — 展示"用系统方法优化 AI 产品"的能力

## 二、综合分设计

### 2.1 公式

```
composite = intent×0.25 + severity×0.20 + risk_f1×0.20
          + evidence_recall×0.15 + no_auto_send×0.10
          + fallback×0.10
```

**护栏指标（不计入综合分，只监控）:**
- `must_human_review_accuracy` — 路由准确性，单独追踪

### 2.2 权重理由

| 指标 | 权重 | 理由 |
|------|------|------|
| intent_accuracy | 0.25 | 核心功能，分类对了才能正确路由 |
| severity_accuracy | 0.20 | 影响响应优先级 |
| risk_flag_f1 | 0.20 | 安全相关，漏检有风险 |
| evidence_doc_type_recall | 0.15 | 影响回复质量 |
| no_auto_send_compliance | 0.10 | 安全门禁，已接近 100% |
| fallback_correctness | 0.10 | 降级正确性 |

**未计入综合分的指标:**
| must_human_review_accuracy | 护栏 | 路由准确性，单独监控不参与优化 |

### 2.3 基线分数

基于当前性能（101 条工单）:

```
intent:      53.5%  → 0.535 × 0.25 = 0.13375
severity:    54.5%  → 0.545 × 0.20 = 0.10900
risk_f1:     29.8%  → 0.298 × 0.20 = 0.05960
evidence:    43.2%  → 0.432 × 0.15 = 0.06480
no_auto:    100.0%  → 1.000 × 0.10 = 0.10000
fallback:    90.1%  → 0.901 × 0.10 = 0.09010
─────────────────────────────────────────────────
composite baseline:                    0.55725
```

## 三、系统架构

### 3.1 模块结构

```
src/ticketpilot/optimizer/
├── __init__.py
├── __main__.py        # CLI 入口 (python -m ticketpilot.optimizer)
├── engine.py          # 主循环控制器
├── evaluator.py       # 评测运行器（复用 evaluation/）
├── diagnostics.py     # 诊断引擎
├── fixer.py           # 修复生成器
├── verifier.py        # 验证器（测试+评测对比）
├── history.py         # 迭代历史管理
├── reporter.py        # 最终报告生成
├── git_ops.py         # Git 操作封装
└── config.py          # 优化器配置
```

### 3.2 数据流

```
手动触发
  ↓
engine.py: 初始化基线
  ├── evaluator.load_dataset() → 加载 101 条工单
  ├── evaluator.run_baseline() → 拿到基线 EvaluationSummary
  └── history.init() → 初始化 JSONL 文件
  ↓
┌─── 循环 N=1..20 ───────────────────────────────┐
│                                                   │
│  ① evaluator.run_current()                       │
│     ├── load_eval_dataset(tickets, golden)        │
│     ├── for each ticket: predict_from_pipeline()  │
│     └── compute_evaluation_summary(predictions)   │
│     → EvaluationSummary (12 aggregate + per-case) │
│                                                   │
│  ② diagnostics.analyze(summary, dataset)          │
│     → 逐条分析 mismatch (CaseResult 字段)         │
│     → 归类错误模式                                │
│     → rank_by_fix_gain() 排序                    │
│                                                   │
│  ③ fixer.apply_fix(diagnosis)                    │
│     → 选最高收益的修复                            │
│     → 生成修复方案 (FixConfig / FixKeywords)      │
│     → 应用修复（改文件）                          │
│                                                   │
│  ④ verifier.run(old_summary)                     │
│     → 跑全量测试（pytest）                        │
│     → 跑评测（对比 old_summary vs new_summary）   │
│     → 退步检测                                    │
│                                                   │
│  ⑤ 验证通过 → git_ops.commit()                   │
│     验证失败 → fixer.rollback() + 换下一个修复    │
│                                                   │
│  ⑥ history.record()                              │
│     → 追加到 optimization_history.jsonl           │
│                                                   │
└─────────────────────────────────────────────────┘
  ↓
reporter.generate()
  → optimization_report.md
```

## 四、诊断引擎（核心）

### 4.1 诊断流程

```python
from ticketpilot.evaluation.schemas import EvaluationSummary

def analyze(eval_summary: EvaluationSummary, eval_dataset: dict):
    """分析 mismatch，返回按修复收益排序的诊断列表。"""
    # 1. 逐条分析 mismatch
    mismatches = []
    for case_id, case in eval_summary.results.items():
        if case.metrics.intent_accuracy is False:
            mismatches.append({
                "case_id": case_id,
                "type": "intent_mismatch",
                "expected": case.golden.expected_issue_type.value,
                "predicted": case.prediction.predicted_issue_type.value,
                "text": eval_dataset[case_id].ticket_text[:100],
            })
        if case.metrics.risk_flag_metrics.exact_match is False:
            mismatches.append({
                "case_id": case_id,
                "type": "risk_flag_mismatch",
                "expected": [f.value for f in case.golden.expected_risk_flags],
                "predicted": [f.value for f in case.prediction.predicted_risk_flags],
            })
        if case.metrics.evidence_doc_type_recall < 1.0:
            mismatches.append({
                "case_id": case_id,
                "type": "evidence_gap",
                "expected_doc_types": case.golden.evidence_doc_types,
                "predicted_doc_types": case.prediction.predicted_evidence_doc_types,
            })
        # severity, fallback, no_auto_send 类似...

    # 2. 归类错误模式
    patterns = classify_patterns(mismatches)

    # 3. 按修复收益排序
    ranked = rank_by_fix_gain(patterns)

    return ranked
```

### 4.2 错误模式分类

| 模式 | 诊断方法 | 修复方向 | 收益计算 |
|------|---------|---------|---------|
| **intent混淆** | 统计 A→B 的混淆矩阵 | 调整关键词规则 | 修对数 / 总错数 |
| **risk漏检** | 统计哪些 flag 被漏 | 补充风险关键词 | 修对数 / 总错数 |
| **risk误检** | 统计哪些 flag 多检 | 精简风险关键词 | 修对数 / 总错数 |
| **severity错** | 统计 severity 分布 | 调整 flag 计数阈值（L5，改 assessor.py） | 修对数 / 总错数 |
| **evidence缺失** | 统计哪些 doc_type 没召回 | 补充知识库 / 调 reranker | 修对数 / 总错数 |
| **confidence误判** | 统计 confidence level 分布 | 调整 confidence 阈值 | 修对数 / 总错数 |

### 4.3 混淆矩阵示例

```
Intent 混淆矩阵 (当前):
                predicted
expected    REFUND  RETURN_EX  ACCOUNT_I  TECHNICAL_I  PRODUCT_C  LOGISTICS  COMPLAINT  OTHER
REFUND         12      0         0          0           0          0          0        3
RETURN_EX       1     8          0          0           0          0          0        1
ACCOUNT_I       0      0         6          0           0          0          0        2
TECHNICAL_I     0      0         0          5           0          0          0        3
PRODUCT_C       0      0         0          0           4          0          0        2
LOGISTICS       0      0         0          0           0          7          0        1
COMPLAINT       0      0         0          0           0          0          6        2
OTHER           2      1         1          1           0          0          0        4

→ REFUND 有 3 条被误分为 OTHER → 可能缺少某些退款关键词
→ COMPLAINT 有 2 条被误分为 OTHER → 可能缺少某些投诉关键词
```

### 4.4 修复收益排序

```python
# 收益 = 修复后预期提升的综合分
# 简化计算: 修对数 × 该指标权重 / 总工单数

# 例:
#   修 intent 混淆 (REFUND→OTHER): 修对 3 条 × 0.25 / 101 = +0.0074
#   修 risk 漏检 (COMPLAINT_RISK): 修对 5 条 × 0.20 / 101 = +0.0099
#   调 confidence 阈值: 影响 15 条路由 × 0.10 / 101 = +0.0149
#
# → 按收益排序: confidence阈值 > risk漏检 > intent混淆
```

## 五、修复机制

### 5.1 修复类型（按安全等级排序）

| 级别 | 类型 | 修改范围 | 风险 | 回滚难度 |
|------|------|---------|------|---------|
| L1 | 阈值调整 | `config/__init__.py` 数值 | 低 | 简单 |
| L1 | 权重调整 | `confidence/scorer.py` 字典 | 低 | 简单 |
| L2 | 关键词补充 | `classification/rules.py` | 中 | 简单 |
| L2 | 风险关键词 | `risk/rules.py` | 中 | 简单 |
| L3 | Reranker 配置 | `retrieval/reranker_config.py` (dataclass) | 中 | 简单 |
| L4 | 知识库补充 | `data/knowledge/` | 中 | 中等 |
| L5 | 代码逻辑 | `risk/assessor.py` (severity 逻辑) | 高 | 需要测试 |

> **注意**: severity 计算在 `risk/assessor.py` 中硬编码（flag 计数阈值），
> 不在 `config/__init__.py`。调整 severity 需要修改代码逻辑（L5）。

### 5.2 修复生成逻辑

```python
def generate_fix(diagnosis):
    if diagnosis.type == "confidence_misroute":
        return FixConfig(
            file="src/ticketpilot/config/__init__.py",
            changes={"HIGH": new_high, "MEDIUM": new_medium},
        )

    elif diagnosis.type == "intent_confusion":
        return FixKeywords(
            file="src/ticketpilot/classification/rules.py",
            rule=diagnosis.source_intent,
            add_keywords=diagnosis.suggested_keywords,
        )

    elif diagnosis.type == "risk_miss":
        return FixKeywords(
            file="src/ticketpilot/risk/rules.py",
            rule=diagnosis.missed_flag,
            add_keywords=diagnosis.suggested_keywords,
        )

    elif diagnosis.type == "evidence_gap":
        # reranker_config.py 是 dataclass，需要构造有效实例
        return FixReranker(
            file="src/ticketpilot/retrieval/reranker_config.py",
            changes=diagnosis.suggested_weights,
        )
```

### 5.3 修复约束

每次修复必须满足:
1. **最小改动** — 只改必要的文件，不改无关代码
2. **向后兼容** — 不改变公共 API
3. **可测试** — 改完后测试必须全通过
4. **可回滚** — 每次修改独立 Git commit

## 六、验证机制

### 6.1 三层验证

```
Layer 1: 单元测试
  pytest tests/unit/ -v
  → 必须全通过

Layer 2: 评测对比
  运行 101 条工单评测
  → composite 分数不能下降
  → 任何单指标下降不超过 2%

Layer 3: 退步检测
  逐条对比修改前后
  → 已修对的 case 不能重新变错
  → 新修对的 case 必须 ≥ 1
```

### 6.2 回滚条件

```python
def should_rollback(old_scores, new_scores, old_correct_ids, new_correct_ids):
    # 条件 1: composite 下降
    if new_scores.composite < old_scores.composite:
        return True, "composite decreased"

    # 条件 2: 任何单指标下降超过 2%
    for metric in ["intent", "severity", "risk_f1", "evidence", "no_auto", "fallback"]:
        if new_scores[metric] < old_scores[metric] - 0.02:
            return True, f"{metric} decreased by >2%"

    # 条件 3: 修对数为 0
    fixed = len(new_correct_ids - old_correct_ids)
    if fixed == 0:
        return True, "no cases fixed"

    # 条件 4: 测试失败
    if test_failures > 0:
        return True, "tests failed"

    return False, "all good"
```

## 七、历史记录

### 7.1 JSONL 格式

每行一个 JSON 对象，记录一轮迭代:

```json
{
  "iteration": 1,
  "timestamp": "2026-06-10T15:00:00+08:00",
  "scores": {
    "composite": 0.557,
    "intent": 0.535,
    "severity": 0.545,
    "risk_f1": 0.298,
    "evidence_recall": 0.432,
    "no_auto_send": 1.0,
    "fallback": 0.901
  },
  "fix": {
    "type": "keyword_addition",
    "file": "src/ticketpilot/classification/rules.py",
    "description": "添加退款相关关键词到 REFUND 规则",
    "keywords_added": ["退款超时", "退款未到账", "退不到账"],
    "cases_fixed": ["T003", "T017", "T042"],
    "cases_broken": []
  },
  "delta": {
    "composite": 0.0074,
    "intent": 0.0297,
    "cases_improved": 3,
    "cases_regressed": 0
  },
  "test_result": "pass",
  "git_commit": "abc1234"
}
```

### 7.2 状态持久化（`--continue` 支持）

状态存储在 `optimization_state.json`:

```json
{
  "last_iteration": 5,
  "last_scores": {"composite": 0.612, "intent": 0.584, ...},
  "started_at": "2026-06-10T15:00:00",
  "updated_at": "2026-06-10T15:22:00"
}
```

每次迭代完成后更新。`--continue` 读取此文件，跳过已完成的轮次。

### 7.3 最终报告模板

```markdown
# 自迭代优化报告

**运行时间**: 2026-06-10 15:00 ~ 15:45 (45 分钟)
**总轮次**: 20 轮（有效修复 15 轮，回滚 5 轮）

## 综合分变化

| 指标 | 基线 | 最终 | 变化 | 进度条 |
|------|------|------|------|--------|
| Composite | 0.557 | 0.712 | +0.155 (+27.8%) | ████████████████░░░░ |
| Intent | 53.5% | 78.2% | +24.7% | ████████████████████░░░░░ |
| Severity | 54.5% | 72.3% | +17.8% | ███████████████░░░░░░░░░░ |
| Risk F1 | 29.8% | 58.4% | +28.6% | ████████████████████████░░ |
| Evidence | 43.2% | 65.1% | +21.9% | ██████████████████░░░░░░░ |
| No-auto | 100% | 100% | ±0% | ██████████████████████████ |
| Fallback | 90.1% | 94.3% | +4.2% | ████████████████████████░░ |

## 每轮迭代明细

| 轮 | 修复类型 | 改动文件 | 综合分变化 | 修对 | 修错 |
|----|---------|---------|-----------|------|------|
| 1 | 关键词补充 | rules.py | +0.007 | 3 | 0 |
| 2 | 阈值调整 | config.py | +0.012 | 8 | 0 |
| 3 | 权重调整 | scorer.py | +0.005 | 2 | 0 |
| ... | | | | | |

## Top 修复效果

1. **添加退款超时关键词** → intent +4.7%, 3 cases fixed
2. **调整 confidence HIGH 阈值** → no_auto_send +0%, 路由更准确
3. **补充投诉风险关键词** → risk_f1 +8.2%, 5 cases fixed

## Git 提交历史

共 15 次提交，每次提交对应一轮有效修复。
可通过 `git log --oneline` 查看完整历史。
```

## 八、CLI 入口

### 8.1 入口文件

创建 `src/ticketpilot/optimizer/__main__.py`:

```python
"""python -m ticketpilot.optimizer"""
import argparse
from .engine import OptimizationEngine

def main():
    parser = argparse.ArgumentParser(description="TicketPilot Auto-Optimizer")
    parser.add_argument("--rounds", type=int, default=20, help="Max iterations")
    parser.add_argument("--diagnose-only", action="store_true", help="Diagnose without fixing")
    parser.add_argument("--continue", dest="continue_run", action="store_true",
                        help="Continue from last iteration")
    parser.add_argument("--dry-run", action="store_true", help="Simulate without modifying files")
    parser.add_argument("--history", action="store_true", help="Show optimization history")
    args = parser.parse_args()

    engine = OptimizationEngine(args)
    engine.run()
```

### 8.2 CLI 用法

```bash
# 基本用法
python -m ticketpilot.optimizer

# 指定轮次
python -m ticketpilot.optimizer --rounds 20

# 只跑诊断（不修复）
python -m ticketpilot.optimizer --diagnose-only

# 从上次中断处继续（读取 optimization_state.json）
python -m ticketpilot.optimizer --continue

# 干跑（不实际修改文件）
python -m ticketpilot.optimizer --dry-run

# 查看历史
python -m ticketpilot.optimizer --history
```

### 8.3 CLI 预期输出

```
$ python -m ticketpilot.optimizer --rounds 5

═══ TicketPilot Auto-Optimizer ═══
Loading eval dataset: 101 tickets
Baseline scores: composite=0.557 intent=0.535 severity=0.545 risk_f1=0.298

─── Round 1/5 ───
  Evaluating... intent=0.535 severity=0.545 risk_f1=0.298
  Diagnosing... found 47 mismatches, top fix: intent_keywords(REFUND)
  Applying fix: add 3 keywords to REFUND rules
  Verifying... tests: 1801/1801 pass, eval: composite=0.564 (+0.007)
  ✅ Committed: abc1234 "iter1: add refund keywords (+0.007 composite)"

─── Round 2/5 ───
  ...

═══ Report ═══
Composite: 0.557 → 0.612 (+0.055, +9.9%)
Git commits: 5
Duration: 12 minutes
Report saved to: reports/optimization/optimization_report.md
```

## 九、实现计划

### Phase 1: 基础框架 (Task 1-3)
- [ ] Task 1: 创建 optimizer/ 模块结构 + `__init__.py` + `__main__.py`
  - 验证: `python -c "from ticketpilot.optimizer import engine"` 无报错
- [ ] Task 2: 实现 evaluator.py（复用现有 evaluation/）
  - 验证: `evaluator.load_dataset()` 返回 101 条工单
- [ ] Task 3: 实现 history.py（JSONL 读写）
  - 验证: 写入→读取→内容一致

### Phase 2: 诊断引擎 (Task 4-6)
- [ ] Task 4: 实现 diagnostics.py（mismatch 分析）
  - 测试: 用 mock EvaluationSummary 验证 mismatch 提取
- [ ] Task 5: 实现错误模式分类
  - 测试: 用已知错误模式验证分类正确
- [ ] Task 6: 实现修复收益排序
  - 测试: 验证排序逻辑（高收益排前面）

### Phase 3: 修复机制 (Task 7-9)
- [ ] Task 7: 实现 fixer.py（L1 阈值/权重调整）
  - 测试: 修改 config → 验证修改生效 → 回滚验证
- [ ] Task 8: 实现 fixer.py（L2 关键词补充）
  - 测试: 添加关键词 → 验证分类变化
- [ ] Task 9: 实现 git_ops.py（提交封装）
  - 测试: 创建临时文件 → commit → 验证 git log

### Phase 4: 验证与循环 (Task 10-12)
- [ ] Task 10: 实现 verifier.py（三层验证）
  - 测试: 用已知好/坏修复验证回滚逻辑
- [ ] Task 11: 实现 engine.py（主循环）
  - 测试: 3 轮小规模运行，验证完整流程
- [ ] Task 12: 实现 reporter.py（最终报告）
  - 测试: 用 mock 数据验证报告格式

### Phase 5: 端到端验证 (Task 13-14)
- [ ] Task 13: 端到端测试（3 轮小规模）
  - 验证: 完整流程跑通，报告生成正确
- [ ] Task 14: 编写单元测试（≥70% 覆盖率）
  - 验证: `pytest tests/unit/ -v` 全通过

## 十、风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 修复导致退步 | 部分 case 变差 | 三层验证 + 自动回滚 |
| 诊断不准 | 修复方向错误 | 收益排序 + 最小改动原则 |
| 20 轮不够 | 优化不充分 | 记录历史，可多次运行 |
| 过拟合评测数据 | 泛化能力差 | 评测集覆盖 8 类场景 |
| Git 历史混乱 | 难以 review | 规范 commit message |

## 十一、与现有模块的关系

```
现有模块（不修改）:
├── evaluation/        ← 优化器调用，不修改
├── classification/    ← 优化器可能修改 rules.py
├── risk/              ← 优化器可能修改 rules.py
├── confidence/        ← 优化器可能修改 scorer.py
├── retrieval/         ← 优化器可能修改 reranker_config.py
├── experiment/        ← 可复用 A/B 框架
├── feedback/          ← 可复用 threshold_advisor
└── skills/            ← 可复用 reflector 模式

新增模块:
└── optimizer/         ← 本文档设计的内容
```
