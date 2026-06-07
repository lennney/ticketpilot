# TicketPilot v2 PRD (带验收钩子)

> PM: Hermes | Tech: Claude Code | Date: 2026-06-07

---

## 需求 1: 法律威胁意图分类

### 背景
DEMO-005 "请联系我们律师，准备起诉" 被分类为 OTHER，应该归入 COMPLAINT。

### 实现
- 文件: `src/ticketpilot/classification/rules.py`
- 在 COMPLAINT 规则的 keywords 末尾添加: "律师函", "起诉", "法院传票", "法律诉讼", "仲裁"

### 验收钩子 ✅
完成上述修改后，运行以下命令并粘贴输出：

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python3 -c "
from ticketpilot.classification.classifier import IntentClassifier
from ticketpilot.schema.ticket import IntentClass
c = IntentClassifier()
tests = [
    ('请联系我们律师，准备起诉你们公司', 'complaint'),
    ('我要向法院起诉', 'complaint'),
    ('收到律师函了', 'complaint'),
    ('我要退款', 'refund'),
    ('投诉你们态度差', 'complaint'),
]
for text, expected in tests:
    result = c.classify(text)
    status = '✅' if result.intent.value == expected else '❌'
    print(f'{status} \"{text}\" → {result.intent.value} (expected: {expected}, conf: {result.confidence})')
"
```

期望输出: 所有行都是 ✅

---

## 需求 2: 多信号置信度评分

### 背景
当前所有关键词匹配都返回 0.80，4级分级系统形同虚设。

### 实现
1. 在 `src/ticketpilot/config/__init__.py` 添加:
   ```python
   CONFIDENCE_KEYWORD_WITH_ORDER = 0.88
   CONFIDENCE_KEYWORD_LONG_TEXT = 0.82
   ```
   并将 CONFIDENCE_HIGH 从 0.8 改为 0.78

2. 在 `src/ticketpilot/classification/classifier.py` 的 `matched_keyword_len >= 2` 分支:
   - 检查订单号 `re.search(r"\d{5,}", text)` → 0.88
   - 检查文本长度 `len(text) > 20` → 0.82
   - 默认 → 0.78

3. 在 `src/ticketpilot/drafting/schemas.py` 的 `confidence_level` 属性:
   - 将 `if self.confidence > CONFIDENCE_HIGH:` 改为 `>=`

### 验收钩子 ✅
完成上述修改后，运行以下命令并粘贴输出：

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python3 -c "
from ticketpilot.classification.classifier import IntentClassifier
c = IntentClassifier()
tests = [
    ('我要退款，订单号123456', 0.88, '有订单号'),
    ('我要投诉你们态度太差了服务很不好', 0.82, '长文本'),
    ('我要退款', 0.78, '短文本'),
    ('12315投诉', 0.95, '强指标'),
]
for text, expected_conf, desc in tests:
    result = c.classify(text)
    status = '✅' if abs(result.confidence - expected_conf) < 0.01 else '❌'
    print(f'{status} {desc}: {result.confidence} (expected: {expected_conf})')
"
```

期望输出: 所有行都是 ✅

---

## 需求 3: 修复集成测试

### 背景
`test_cli_pipeline_mode_works` 失败，因为 CLI 不支持 `--prediction-mode pipeline`。

### 实现
- 文件: `scripts/run_eval.py`
- 添加 `--prediction-mode` 参数 (choices: file, pipeline)
- 当 mode=pipeline 时，使用 `predict_from_pipeline()` 生成预测
- 当 mode=file 时，保持原有行为 (需要 --predictions 参数)

### 验收钩子 ✅
完成上述修改后，运行以下命令并粘贴输出：

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python -m pytest tests/integration/test_evaluation_pipeline.py -v --tb=short 2>&1 | tail -10
```

期望: 所有测试 PASSED，0 FAILED

---

## 全局验收 ✅

所有需求完成后，运行以下命令并粘贴输出：

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python -m pytest --tb=no -q 2>&1 | tail -3
```

期望: `X passed, 0 failed`

然后运行 demo:

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python scripts/generate_product_evidence.py 2>&1 | grep -E "DEMO-005|Confidence:|SUMMARY" -A 5
```

期望:
- DEMO-005 的 Intent 是 complaint (不是 other)
- Confidence 分布有 3+ 个不同值

最后 commit:

```bash
cd /home/hermes/ticketpilot && git add -A && git commit -m "feat: legal intent classification + multi-signal confidence scoring"
```

---

## 约束
- 不改变路由逻辑
- 不新增 IntentClass 枚举
- 所有现有测试必须继续通过
