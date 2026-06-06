# TicketPilot 评测体系升级方案

> 目标：从"自建关键词overlap + 静态数据"升级为"DeepEval LLM-as-Judge + 真实pipeline + 组件级指标"

---

## 一、现状问题

| 问题 | 严重度 | 说明 |
|------|--------|------|
| faithfulness/relevancy用关键词overlap | 🔴 | 中文按空格split无效，所有case卡0.5分 |
| 评测没接真实pipeline | 🔴 | DeepEval跑在静态生成数据上，不测实际系统 |
| 没有检索质量指标 | 🟡 | 核心卖点hybrid retrieval没有recall@k/MRR |
| 没有guardrail合规测试 | 🟡 | PII/幻觉/no-auto-send写了但没测 |
| 评测数据只有10条 | 🟡 | 统计上无意义 |
| 多agent架构没测 | 🟡 | multi_agent模块空壳，orchestrator没评测 |

---

## 二、升级方案（4个模块）

### Module 1: 接入DeepEval到真实Pipeline（核心）

**改动文件：** `scripts/run_eval.py` → 重写为 `scripts/run_pipeline_eval.py`

**思路：**
- 用现有的 `agent_eval_dataset.json`（10条）+ 从知识库自动生成扩充到50+条
- 每条case跑完整pipeline：intake → classification → retrieval → draft
- 用DeepEval的LLM-as-Judge（DeepSeek）评测faithfulness/relevancy
- 保留intent准确率、has_citations等自定义指标

**指标体系（两层）：**

| 层 | 指标 | 来源 | 目标 |
|----|------|------|------|
| RAG质量 | Faithfulness | DeepEval | ≥0.7 |
| RAG质量 | Answer Relevancy | DeepEval | ≥0.7 |
| RAG质量 | Contextual Precision | DeepEval | ≥0.7 |
| RAG质量 | Contextual Recall | DeepEval | ≥0.7 |
| 业务 | Intent Accuracy | 自定义 | ≥0.9 |
| 业务 | Citation Coverage | 自定义 | ≥0.8 |
| 业务 | Guardrail Pass Rate | 自定义 | ≥0.95 |

### Module 2: 检索质量评测

**新增文件：** `src/ticketpilot/evaluation/retrieval_eval.py`

**指标：**
- Recall@K: 在top-K结果中命中golden evidence的比例
- MRR (Mean Reciprocal Rank): 第一个正确结果的排名倒数
- Context Precision: 检索结果中相关文档的比例

**数据要求：** 每条eval case需要标注 `expected_evidence_ids`（golden evidence）

### Module 3: Guardrail合规评测

**新增文件：** `src/ticketpilot/evaluation/guardrail_eval.py`

**测试项：**
- PII检测：注入手机号/身份证/银行卡，验证被拦截
- 幻觉检测：注入强声明，验证被标记
- No-auto-send：验证pipeline输出包含must_human_review标记
- Input验证：注入prompt injection，验证被拦截

### Module 4: 评测数据扩充

**方案：**
1. 手动编写40条（覆盖6大intent + 边界case + 对抗case）
2. 合并现有10条 → 共50条
3. 每条标注：expected_intent, expected_risk_flags, context, ground_truth

**分类覆盖：**

| 类别 | 数量 | 覆盖场景 |
|------|------|---------|
| refund | 10 | 7天无理由、质量问题、超期、三倍赔偿 |
| complaint | 10 | 食品安全、客服态度、法律威胁、个人信息泄露 |
| logistics | 8 | 丢件、海关扣留、延迟、签收争议 |
| technical_issue | 8 | 支付失败、功能bug、登录异常 |
| account_issue | 7 | 被盗、冻结、密码找回 |
| 边界/对抗 | 7 | 模糊意图、多意图、prompt注入、超长输入 |

---

## 三、实施计划

| 阶段 | 任务 | 估时 |
|------|------|------|
| Phase 1 | Module 4: 扩充评测数据到50条 | 1h |
| Phase 2 | Module 1: 重写pipeline eval接入DeepEval | 1.5h |
| Phase 3 | Module 2: 新增检索质量评测 | 1h |
| Phase 4 | Module 3: 新增guardrail合规评测 | 0.5h |
| Phase 5 | 集成测试 + 跑一次完整eval + 修bug | 1h |

**总计约5小时**，建议按Phase 1→2→3→4→5顺序执行。

---

## 四、文件变更预览

```
新增:
  scripts/run_pipeline_eval.py          # 新的端到端评测脚本
  src/ticketpilot/evaluation/
    retrieval_eval.py                   # 检索质量评测
    guardrail_eval.py                   # Guardrail合规评测
  data/eval/
    agent_eval_dataset_v2.json          # 扩充后的50条评测数据

修改:
  src/ticketpilot/evaluation/agent_eval.py  # 移除烂的keyword overlap，接入DeepEval
  reports/eval/                              # 新增评测报告
```

---

## 五、预期结果

升级后跑一次完整eval，输出类似：

```
=== TicketPilot Pipeline Evaluation ===

RAG Quality (DeepEval Judge: deepseek-chat)
  Faithfulness:        0.82 (threshold: 0.7) ✅
  Answer Relevancy:    0.78 (threshold: 0.7) ✅
  Contextual Precision: 0.75 (threshold: 0.7) ✅
  Contextual Recall:   0.71 (threshold: 0.7) ✅

Business Metrics
  Intent Accuracy:     94.0% (threshold: 90%) ✅
  Citation Coverage:   88.0% (threshold: 80%) ✅
  Guardrail Pass Rate: 96.0% (threshold: 95%) ✅

Retrieval Quality
  Recall@5:            0.85
  MRR:                 0.78

Total: 50 cases | Passed: 45 | Failed: 5 | Pass Rate: 90.0%
```
