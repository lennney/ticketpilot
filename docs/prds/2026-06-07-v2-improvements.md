# TicketPilot v2 产品需求文档 (PRD)

> PM: Hermes | Tech: Claude Code (MIMO) | Date: 2026-06-07

---

## 背景

Demo 跑了 10 张工单，发现 3 个产品问题：

1. **法律威胁被分类为"未知"** — DEMO-005 "请联系我们律师，准备起诉" → intent=OTHER
2. **置信度系统形同虚设** — 90% 工单都是 0.80，4 级分级实际只有 2 级
3. **有一个集成测试失败** — CLI 参数解析问题

---

## 需求 1: 法律威胁意图分类

### 问题
用户说"律师起诉"，系统分类为 OTHER。风险评估正确识别了 legal_risk，路由也正确到了 ComplaintAgent，但意图分类失败。

### 产品决策
不新增 IntentClass。法律威胁本质上是最高级别的投诉，应该归入 COMPLAINT。

### 验收标准
- [ ] "请联系我们律师，准备起诉你们公司" → intent=complaint, confidence≥0.78
- [ ] "我要向法院起诉" → intent=complaint, confidence≥0.78
- [ ] "收到律师函了" → intent=complaint, confidence≥0.78
- [ ] 现有 COMPLAINT 关键词（投诉、差评等）行为不变
- [ ] 现有非 COMPLAINT 意图的分类行为不变

### 实现指引
- 文件: `src/ticketpilot/classification/rules.py`
- 在 COMPLAINT 规则的 keywords 列表末尾添加: "律师函", "起诉", "法院传票", "法律诉讼", "仲裁"
- 不要修改其他规则

---

## 需求 2: 多信号置信度评分

### 问题
当前分类器: 任何 2+ 字符关键词匹配 → 0.80，无匹配 → 0.50。
结果: 10 张工单中 9 张都是 0.80，4 级分级系统（HIGH/MEDIUM/LOW/CRITICAL）形同虚设。

### 产品决策
引入多信号评分——除了关键词匹配外，还考虑订单号存在和文本长度。
这样"退款+订单号123456"比模糊的投诉有更高置信度。

### 验收标准
- [ ] 强指标匹配（如"12315投诉"）→ 0.95（不变）
- [ ] 关键词匹配 + 文本含订单号（r"\d{5,}"）→ 0.88
- [ ] 关键词匹配 + 文本长度 > 20 字符 → 0.82
- [ ] 关键词匹配（默认）→ 0.78
- [ ] 1 字符关键词匹配 → 0.70（不变）
- [ ] 无匹配 → 0.50（不变）
- [ ] Demo 10 张工单的置信度分布应至少有 3 个不同值（不是只有 0.80 和 0.50）

### 实现指引
- 文件: `src/ticketpilot/classification/classifier.py`
- 修改 Phase 2 的置信度计算逻辑
- 在 `matched_keyword_len >= 2` 分支中，先检查订单号模式，再检查文本长度
- 使用 `re.search(r"\d{5,}", text)` 检测订单号
- 新增 config 常量:
  - `CONFIDENCE_KEYWORD_WITH_ORDER = 0.88` (在 `src/ticketpilot/config/__init__.py`)
  - `CONFIDENCE_KEYWORD_LONG_TEXT = 0.82`

---

## 需求 3: 修复集成测试

### 问题
`tests/integration/test_evaluation_pipeline.py::TestPipelinePredictions::test_cli_pipeline_mode_works` 失败。
错误: `__main__.py: error: the following arguments are required: --predictions`

### 验收标准
- [ ] 该测试通过
- [ ] 不改变测试的意图（测试 CLI pipeline 模式能正常工作）
- [ ] 其他测试不受影响

### 实现指引
- 先运行测试查看完整错误: `python -m pytest tests/integration/test_evaluation_pipeline.py::TestPipelinePredictions::test_cli_pipeline_mode_works -v --tb=long`
- 检查测试代码和被测 CLI 的参数定义是否匹配
- 修复测试代码或 CLI 参数定义

---

## 全局约束

1. **不改变路由逻辑** — Orchestrator 的 legal_risk 覆盖已经正确
2. **不新增 IntentClass** — 法律威胁归入 COMPLAINT
3. **所有现有测试必须通过** — 修改后运行 `python -m pytest --tb=no -q`
4. **分类器测试单独验证** — `python -m pytest tests/unit/test_classifier.py -v`

---

## 完成后

1. 运行 demo: `python scripts/generate_product_evidence.py`
2. 确认 DEMO-005 不再是 OTHER
3. 确认置信度分布有 3+ 个不同值
4. 全量测试通过
5. Git commit
