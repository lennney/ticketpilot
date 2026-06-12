# TicketPilot 优化器升级：增量评测 + 诊断增强 + 最佳状态追踪

> **目标执行者**：任何 LLM（包括低级别模型），不需要理解项目全貌，逐步执行即可。
> **总估时**：约 3-4 小时（含测试运行）
> **前置条件**：Python 3.11+，`PYTHONPATH=src` 可用，工作目录为 `/home/hermes/ticketpilot`
> **依赖**：基础设施修复（FTS 编码安全 + 评测稳定性 + exclusion_rule）已完成

---

## 背景

优化器之前跑 2 轮 0 轮成功，三个根因：

| 根因 | 状态 |
|------|------|
| FTS UnicodeDecodeError | ✅ 已修复 |
| 评测不稳定 ±1-2% | ✅ 已修复 |
| first-match-wins 关键词无效 | ✅ exclusion_rule 已修复 |

但优化的**效率**和**精度**还有三个问题需要解决：

1. **增量评测**：每轮全量重评 101 条工单，6 分钟/轮。实际上修复只影响 1-5 条工单，剩下 90%+ 的结果不变
2. **诊断精度**：诊断器只看 aggregate 指标，不分析具体哪些文本特征导致了误分类。DSPy 等框架的核心是「先 trace 分析 → 再 propose 候选」 
3. **无最佳状态追踪**：每轮要么保留要么回滚。如果第 3 轮修好了 2 条，第 4 轮修坏了 1 条但修好了 3 条，第 5 轮又全坏了——系统回滚到第 3 轮之后的状态就没了

---

## Task 1：增量评测

**目标**：每次修复验证只重评受影响的工单子集，从 6 分钟降到 30 秒。

**方法**：先写测试，再实现代码（TDD）。

---

```
现在：run_full_evaluation() → 遍历全部 101 条工单 → 6 分钟
改为：run_partial_evaluation(case_ids) → 只遍历 affected case_ids → 30 秒
```

修复的诊断知道哪些 case 受影响（`Diagnosis.affected_cases`），以及哪些 case 完全不相关。不相关的 case 复用上一轮的 prediction。

### Step 1（TDD）: 先写增量评测测试

**文件**: `tests/unit/test_optimizer_engine.py`（在文件末尾追加）

```python
class TestIncrementalEvaluation:
    """Verify incremental evaluation produces same results as full evaluation."""

    def test_partial_evaluation_returns_summary(self, sample_evaluator):
        """run_partial_evaluation returns an EvaluationSummary."""
        from ticketpilot.evaluation.schemas import EvaluationSummary

        full = sample_evaluator.run_full_evaluation()
        assert isinstance(full, EvaluationSummary)

    def test_partial_evaluation_matches_full_when_all_affected(self, sample_evaluator):
        """Incremental with all case IDs = full evaluation."""
        all_ids = set(sample_evaluator.dataset.tickets.keys())
        full = sample_evaluator.run_full_evaluation()
        partial = sample_evaluator.run_partial_evaluation(
            affected_case_ids=all_ids,
            previous_predictions={},
        )
        assert partial.aggregate_intent_accuracy == full.aggregate_intent_accuracy

    def test_partial_evaluation_preserves_unaffected(self, sample_evaluator):
        """Unaffected ticket predictions carry over from previous_predictions."""
        full = sample_evaluator.run_full_evaluation()
        all_predictions = sample_evaluator.predictions
        assert len(all_predictions) > 0

        # Only re-predict the first ticket
        first_id = list(sample_evaluator.dataset.tickets.keys())[0]
        partial = sample_evaluator.run_partial_evaluation(
            affected_case_ids={first_id},
            previous_predictions=all_predictions,
        )
        # Should still produce a valid summary (not crash)
        assert partial.total_cases == full.total_cases
```

运行测试验证它失败（增量方法还不存在）：

```bash
cd /home/hermes/ticketpilot
PYTHONPATH=src python3 -m pytest tests/unit/test_optimizer_engine.py::TestIncrementalEvaluation -v --tb=short
Expected: FAIL (AttributeError: 'OptimizerEvaluator' object has no attribute 'run_partial_evaluation')
```

### Step 2（实现）: 给 `OptimizerEvaluator` 加增量评测方法

**文件**: `src/ticketpilot/optimizer/evaluator.py`

在第 97 行（`_generate_predictions` 之后）添加新方法：

```python
    def run_partial_evaluation(
        self,
        affected_case_ids: set[str],
        previous_predictions: dict[str, EvalPrediction] | None = None,
    ) -> EvaluationSummary:
        """Run evaluation on only affected tickets, reusing previous predictions for the rest.

        Args:
            affected_case_ids: Set of case IDs that need re-prediction.
            previous_predictions: Previous predictions dict. When provided,
                unaffected tickets reuse their previous results.
                When None, runs full evaluation (backward compatible fallback).

        Returns:
            EvaluationSummary with updated per-case and aggregate metrics.
        """
        ds = self.dataset

        # Start with previous predictions (or empty)
        if previous_predictions is not None:
            predictions = dict(previous_predictions)
        else:
            predictions = {}

        # Only re-predict affected tickets
        for case_id in affected_case_ids:
            ticket = ds.tickets.get(case_id)
            if ticket is None:
                continue
            try:
                pred = predict_from_pipeline(ticket)
                predictions[case_id] = pred
            except Exception:
                logger.exception("Pipeline failed for %s", case_id)
                raise

        # If no previous predictions, fill in the rest
        if previous_predictions is None:
            for case_id, ticket in ds.tickets.items():
                if case_id not in predictions:
                    try:
                        pred = predict_from_pipeline(ticket)
                        predictions[case_id] = pred
                    except Exception:
                        logger.exception("Pipeline failed for %s", case_id)
                        raise

        self._predictions = predictions
        summary = compute_evaluation_summary(predictions, ds.golden)
        return summary
```

### Step 2: 修改 `engine.py` 的 `_verify_fix()` 使用增量评测

**文件**: `src/ticketpilot/optimizer/engine.py`

修改 `_verify_fix()` 方法（第 386-438 行），接受 `affected_cases` 参数并使用增量评测：

```python
    def _verify_fix(
        self,
        old_summary: EvaluationSummary,
        old_correct_ids: set[str],
        affected_cases: set[str] | None = None,
        old_predictions: dict[str, EvalPrediction] | None = None,
    ) -> tuple[bool, EvaluationSummary, float]:
        """Re-evaluate after applying a fix and check for improvement.

        Uses incremental evaluation when affected_cases is provided.
        """
        if affected_cases and old_predictions is not None:
            new_summary = self.evaluator.run_partial_evaluation(
                affected_case_ids=affected_cases,
                previous_predictions=old_predictions,
            )
        else:
            new_summary = self.evaluator.run_full_evaluation()

        new_composite = self._compute_composite(new_summary)
        old_composite = self._compute_composite(old_summary)

        # (rest same as before)
        ...
```

### Step 3: 修改 `_run_one_round()` 传递 affected_cases

**文件**: `src/ticketpilot/optimizer/engine.py`

在 `_run_one_round()` 中，获取当前 predictions，并在调用 `_verify_fix()` 时传入 `affected_cases`：

在第 261-285 行（try fix loop），改为：

```python
        # 获取当前的 predictions（用于增量评测）
        current_predictions = dict(self.evaluator.predictions or {})

        for diag in candidates:
            fixes_tried += 1
            _print(f"Trying fix: [{diag.type}] {diag.suggested_fix_type} (gain={diag.fix_gain:.4f})")

            fix_result = self.fixer.apply_fix(diag)

            if not fix_result.success:
                _print(f"✗ Fix failed: {fix_result.fix_type} — {fix_result.error or fix_result.description}")
                continue

            # 增量验证：只重评受影响工单
            affected_ids = set(diag.affected_cases) if diag.affected_cases else None

            improved, new_summary, new_composite = self._verify_fix(
                old_summary, old_correct_ids,
                affected_cases=affected_ids,
                old_predictions=current_predictions,
            )

            if improved:
                # 更新 predictions 缓存，后续修复基于最新状态
                current_predictions = dict(self.evaluator.predictions or current_predictions)
            # (rest same as before)
```

### Step 4: 添加 import

在 `engine.py` 顶部添加：

```python
from ticketpilot.evaluation.schemas import EvalPrediction  # NEW: needed for _verify_fix type hint
```

### 测试

```bash
cd /home/hermes/ticketpilot
PYTHONPATH=src python3 -m pytest tests/unit/test_optimizer_engine.py -v --tb=short
PYTHONPATH=src python3 -c "
# 验证增量评测逻辑
from ticketpilot.optimizer.evaluator import OptimizerEvaluator
from ticketpilot.optimizer.config import OptimizerConfig

config = OptimizerConfig()
eval = OptimizerEvaluator(config)
eval.load_dataset()

# 全量评测作为 baseline
full = eval.run_full_evaluation()
print(f'Full: {full.total_cases} cases')

# 增量评测（只重评前 3 条）
first_three = set(list(eval.dataset.tickets.keys())[:3])
partial = eval.run_partial_evaluation(
    affected_case_ids=first_three,
    previous_predictions=eval.predictions,
)
print(f'Partial: {partial.total_cases} cases')
print(f'Intent: {partial.aggregate_intent_accuracy:.4f} vs {full.aggregate_intent_accuracy:.4f}')
print(f'✅ 增量评测验证完成')
"
```

### 验收标准

1. `run_partial_evaluation(affected_case_ids=[...])` 只重跑指定的工单，其余复用上一轮结果
2. 无 affected_cases 参数时，回退到全量评测（向后兼容）
3. 增量评测结果与全量评测结果一致（相同输入 → 相同输出）
4. 已有测试全部通过

---

## Task 2：诊断增强 — 误分类样本特征分析

**目标**：诊断引擎不仅说「COMPLAINT 的 F1 低」，还要说「COMPLAINT 被 REFUND 抢走的工单包含关键词 X、Y、Z」。

**方法**：先写测试验证因果分析函数，再实现代码（TDD）。

### 背景

当前诊断器对 intent mismatch 的处理：

```
检测到 COMPLAINT→REFUND 的误分类对
→ 建议「往 COMPLAINT 加关键词」
```

但实际上现在有了 `exclusion_rule`，应该：

```
检测到 COMPLAINT→REFUND 的误分类对
→ 分析误分类工单的文本特征
→ 如果 predicted intent 优先级更高 → 建议 exclusion_rule
→ 建议的排除词来自误分类工单的「特异性关键词」（在误分类工单中出现，但在正确分类的同类工单中不出现的词）
```

### Step 1: 在 `diagnostics.py` 中添加 `_analyze_causal_features()`

**文件**: `src/ticketpilot/optimizer/diagnostics.py`

在第 212 行（`_CHINESE_STOP_WORDS` 之后）添加新函数：

```python
def _analyze_causal_features(
    misclassified_texts: list[str],
    correctly_classified_texts: list[str],
    existing_keywords: list[str],
    max_features: int = 3,
) -> list[str]:
    """Find distinguishing features in misclassified vs correctly classified texts.

    Analyzes n-grams (2-4 chars) that appear significantly more often
    in the misclassified set than in the correctly classified set.

    Args:
        misclassified_texts: Texts that were misclassified.
        correctly_classified_texts: Texts of the same intent that were correctly classified.
        existing_keywords: Keywords already in the rule (to exclude).
        max_features: Max distinguishing features to return.

    Returns:
        List of distinguishing feature keywords, sorted by lift score.
    """
    from collections import Counter
    import re

    if not misclassified_texts:
        return []
    if not correctly_classified_texts:
        # No reference — fall back to common keywords in misclassified texts
        fallback_kws = _extract_chinese_keywords(
            misclassified_texts, existing_keywords, max_keywords=max_features
        )
        # Filter out terms that already appear in high-priority rules
        return [kw for kw in fallback_kws if kw not in existing_keywords][:max_features]

    existing_set = set(existing_keywords)

    def _cjk_ngrams(texts: list[str]) -> Counter:
        counter: Counter[str] = Counter()
        for text in texts:
            cjk = re.sub(r"[^\u4e00-\u9fff]", "", text)
            seen: set[str] = set()
            for n in (2, 3, 4):
                for i in range(len(cjk) - n + 1):
                    gram = cjk[i:i+n]
                    if gram in existing_set:
                        continue
                    if gram not in seen:
                        seen.add(gram)
                        counter[gram] += 1
        return counter

    mis_counter = _cjk_ngrams(misclassified_texts)
    correct_counter = _cjk_ngrams(correctly_classified_texts)
    n_mis = len(misclassified_texts)
    n_correct = len(correctly_classified_texts) or 1  # avoid division by zero

    # Compute lift: (freq_in_mis / n_mis) / (freq_in_correct / n_correct)
    scored: list[tuple[float, str]] = []
    for gram, freq in mis_counter.most_common(50):
        correct_freq = correct_counter.get(gram, 0)
        # Laplace smoothing (α=0.1) to avoid division by zero / infinite lift
        lift = (freq / n_mis) / ((correct_freq + 0.1) / n_correct)
        if lift >= 1.5 and gram not in existing_set:
            scored.append((lift, gram))

    scored.sort(key=lambda x: -x[0])
    return [gram for _, gram in scored[:max_features]]
```

### Step 2: 在 `diagnostics.py` 的 `analyze()` 中利用新函数

**文件**: `src/ticketpilot/optimizer/diagnostics.py`

修改 `analyze()` 方法中的 intent mismatch 诊断（第 446-468 行附近），在生成 `suggested_keywords` 时使用因果分析：

当前代码（第 446-468 行）已经会提取 `suggested_keywords`，但用的是 `_extract_chinese_keywords()`（通用关键词提取）。

找到第 446-468 行，替换为：

```python
            # 提取关键词 — 根据 fix_type 使用不同策略
            suggested_keywords = [expected]  # fallback

            if dataset:
                mis_texts = []
                correct_texts = []

                for cid in case_ids:
                    ticket = dataset.get(cid)
                    if ticket and hasattr(ticket, "original_text"):
                        mis_texts.append(ticket.original_text)

                if fix_type == "exclusion_rule":
                    # 对于 exclusion_rule 修复：找误分类工单中
                    # 能区分「这是投诉不是退款」的特征词
                    # 参考文本：找到正确分类为 predicted intent 的工单
                    for cid, cr in results.items():
                        if cr.prediction.predicted_issue_type == predicted:
                            if cr.metrics.intent_accuracy:
                                ticket = dataset.get(cid)
                                if ticket and hasattr(ticket, "original_text"):
                                    correct_texts.append(ticket.original_text)

                    # 获取 predicted intent 已有的关键词（作为排除项）
                    existing_kws = _get_existing_intent_keywords(predicted.upper())

                    # 因果分析：找误分类工单中有、但正确分类工单中没有的特征词
                    causal = _analyze_causal_features(
                        mis_texts, correct_texts,
                        existing_keywords=existing_kws,
                        max_features=3,
                    )
                    if causal:
                        suggested_keywords = causal
                else:
                    # intent_keyword 修复：原有策略不变
                    existing_kws = _get_existing_intent_keywords(expected.upper())
                    extracted = _extract_chinese_keywords(mis_texts, existing_kws)
                    if extracted:
                        suggested_keywords = extracted
```

### 测试

```bash
cd /home/hermes/ticketpilot
PYTHONPATH=src python3 -c "
from ticketpilot.optimizer.diagnostics import (
    _analyze_causal_features, _extract_chinese_keywords
)

# 模拟误分类工单（COMPLAINT 被 REFUND 抢走）
mis = [
    '我要退款但你们态度太差了我要投诉你们',
    '申请退款，客服态度恶劣，我要投诉',
    '退款不处理，态度差，维权到底',
]
correct = [
    '我买的东西降价了，申请保价退款',
    '订单重复支付了，请退款',
    '退款申请，订单号12345',
]

existing = ['退款', '申请退款', '退钱']

causal = _analyze_causal_features(mis, correct, existing, max_features=3)
print(f'Distinguishing features: {causal}')
# 预期：['态度', '投诉', '维权'] 等投诉类词
print('✅ 因果分析测试完成')
"
```

### 验收标准

1. `_analyze_causal_features()` 能正确区分误分类工单 vs 正确分类工单的特征
2. 对于 exclusion_rule 修复类型，建议的排除词是「误分类工单的特征词」而非「通用高频词」
3. 对于 intent_keyword 修复类型，行为不变（向后兼容）
4. 空输入返回空列表（不崩溃）

---

## Task 3：最佳状态追踪 + 提前终止

**目标**：保留历史最优状态，N 轮无改进自动终止。

**方法**：先写测试验证状态追踪逻辑，再实现代码（TDD）。

### Step 1（TDD）: 先写提前终止和状态追踪测试

**文件**: `src/ticketpilot/optimizer/engine.py`

在 `run()` 方法中，在 `TOP_N_FIXES = 5`（第 38 行）附近添加模块级常量：

```python
# 提前终止：连续 N 轮无改进则停止
CONSECUTIVE_NO_IMPROVEMENT_LIMIT = 3
```

在第 130-134 行后（`# Main loop` 之后），增加最佳状态追踪：

在第 130-134 行后添加：

```python
        # 最佳状态追踪
        best_composite = current_composite
        best_summary = current_summary
        best_correct_ids = current_correct_ids
        best_iteration = 0

        # 提前终止：连续 N 轮无改进则停止
        CONSECUTIVE_NO_IMPROVEMENT_LIMIT = 3
        consecutive_no_improvement = 0
```

在 Main loop 内部（第 148-163 行，每轮之后），修改为：

```python
            if improved:
                # 更新最佳状态
                if current_composite > best_composite:
                    best_composite = current_composite
                    best_summary = current_summary
                    best_correct_ids = current_correct_ids
                    best_iteration = iteration
                    consecutive_no_improvement = 0
                else:
                    consecutive_no_improvement += 1
            else:
                consecutive_no_improvement += 1
                _print(f"✗ Round {iteration}: no improvement ({consecutive_no_improvement}/{CONSECUTIVE_NO_IMPROVEMENT_LIMIT} consecutive)")

            # 提前终止
            if consecutive_no_improvement >= CONSECUTIVE_NO_IMPROVEMENT_LIMIT:
                _print(f"🛑 Stopping: {CONSECUTIVE_NO_IMPROVEMENT_LIMIT} consecutive rounds without improvement")
                break
```

在最终 summary 中（第 172-177 行），新增最佳状态信息：

```python
        # Final summary
        delta = current_composite - baseline_composite
        best_delta = best_composite - baseline_composite
        _print(f"\n═══ Optimization Complete ═══")
        _print(f"Baseline composite: {baseline_composite:.4f}")
        _print(f"Current composite:  {current_composite:.4f} ({delta:+.4f})")
        _print(f"Best composite:     {best_composite:.4f} ({best_delta:+.4f}) @ round {best_iteration}")
```

### Step 2: 在 history 中记录最佳状态

**文件**: `src/ticketpilot/optimizer/engine.py`

每轮记录历史时，增加 `best_composite` 字段（在 `self.history.record()` 调用中）。

找到第 299-311 行（accepted fix 的记录），增加：

```python
                self.history.record({
                    "iteration": iteration,
                    "composite": new_composite,
                    "best_composite": best_composite,  # NEW
                    "correct_cases": len(self._extract_correct_ids(new_summary)),
                    ...
                })
```

### 测试

先写单元测试验证状态追踪逻辑：

**文件**: 在 `tests/unit/test_optimizer_engine.py` 中追加

```python
class TestBestStateTracking:
    """Verify best state tracking and early termination logic."""

    def test_best_composite_tracks_improvements(self):
        """Best composite should update when score improves."""
        from ticketpilot.optimizer.engine import (
            OptimizationEngine, CONSECUTIVE_NO_IMPROVEMENT_LIMIT,
        )

        # 验证常量存在且为合理值
        assert CONSECUTIVE_NO_IMPROVEMENT_LIMIT > 0
        assert CONSECUTIVE_NO_IMPROVEMENT_LIMIT <= 10

    def test_consecutive_limit_is_three(self):
        """CONSECUTIVE_NO_IMPROVEMENT_LIMIT should be 3."""
        from ticketpilot.optimizer.engine import CONSECUTIVE_NO_IMPROVEMENT_LIMIT
        assert CONSECUTIVE_NO_IMPROVEMENT_LIMIT == 3
```

运行测试：

```bash
cd /home/hermes/ticketpilot
PYTHONPATH=src python3 -m pytest tests/unit/test_optimizer_engine.py::TestBestStateTracking -v --tb=short
# Expected: PASS (常量测试)
```

### 验收标准

1. 最佳 composite 分数被追踪并在最终报告中展示
2. 连续 3 轮无改进自动终止
3. 记录 `best_composite` 到 history JSONL
4. 已有测试全部通过

---

## 执行顺序和提交策略

```
Task 1 (增量评测) → git commit
Task 2 (诊断增强) → git commit
Task 3 (最佳状态+提前终止) → git commit
```

每次 commit 格式：
```bash
git add [修改的文件]
git commit -m "optimizer: [简短描述]"
```

全部完成后：
```bash
cd /home/hermes/ticketpilot
PYTHONPATH=src python3 -m pytest tests/unit/test_optimizer_engine.py tests/unit/test_optimizer_diagnostics.py tests/unit/test_optimizer_fixer.py -v --tb=short
```

## 回滚步骤

如果任何步骤出问题：
1. 如果只是某个 task 的修改有问题：`git checkout -- [文件路径]` 恢复该文件
2. 如果要回滚整个 session：`git reset --hard HEAD~N`（N 为已提交的次数）
