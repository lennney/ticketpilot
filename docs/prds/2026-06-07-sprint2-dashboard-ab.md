# Sprint 2 PRD: 置信度监控 Dashboard + A/B 阈值实验

> PM: Hermes | Tech: Claude Code | Date: 2026-06-07
> 目标: 让数据可视化，跑一次真实的 A/B 阈值对比

---

## 需求 1: 置信度分布监控页

### 背景

当前 Streamlit 已有基础 Review Console，但没有置信度分布的可视化。多信号置信度实现后，我们有 0.95/0.88/0.82/0.78/0.70/0.50 六个值，需要看分布是否合理。

### 产品决策

新增一个 Streamlit 页面，展示：
1. 置信度分布直方图
2. 四级分级饼图（HIGH/MEDIUM/LOW/CRITICAL）
3. Agent 路由分布柱状图
4. 风险标签热力图

### 实现指引

- 文件: `src/ticketpilot/dashboard/metrics_page.py`（新建）
- 使用 Streamlit + plotly（或 streamlit 原生图表）
- 数据源: 从 `scripts/generate_product_evidence.py` 的输出格式读取，或直接调用 Pipeline 生成

```python
# pages 结构
def render_metrics_page():
    st.header("📊 置信度监控")

    # 1. 从 Pipeline 获取 101 张 eval ticket 的结果
    results = run_pipeline_on_eval_tickets()

    # 2. 置信度分布直方图
    confidences = [r.confidence for r in results]
    st.subheader("置信度分布")
    fig = px.histogram(x=confidences, nbins=20, labels={'x': '置信度', 'y': '工单数'})
    st.plotly_chart(fig)

    # 3. 四级分级饼图
    tiers = [r.confidence_level.value for r in results]
    st.subheader("分级分布")
    tier_counts = Counter(tiers)
    fig = px.pie(names=list(tier_counts.keys()), values=list(tier_counts.values()))
    st.plotly_chart(fig)

    # 4. Agent 路由分布
    agents = [r.agent_used for r in results]
    st.subheader("Agent 路由分布")
    agent_counts = Counter(agents)
    fig = px.bar(x=list(agent_counts.keys()), y=list(agent_counts.values()))
    st.plotly_chart(fig)

    # 5. 风险标签热力图
    st.subheader("风险标签分布")
    risk_data = build_risk_matrix(results)
    st.dataframe(risk_data)
```

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python3 -c "
from ticketpilot.dashboard.metrics_page import run_pipeline_on_eval_tickets
results = run_pipeline_on_eval_tickets()
print(f'✅ 处理工单数: {len(results)}')

# 检查置信度分布
confidences = [r.confidence for r in results]
unique = sorted(set(confidences))
print(f'✅ 置信度种类: {len(unique)} 个 ({unique[:6]}...)')

# 检查四级分布
from collections import Counter
tiers = Counter(r.confidence_level.value for r in results)
print(f'✅ 分级分布: {dict(tiers)}')

# 检查 Agent 分布
agents = Counter(r.agent_used for r in results)
print(f'✅ Agent 分布: {dict(agents)}')
"
```

期望输出:
- 处理工单数: 101
- 置信度种类: ≥ 4 个
- 分级分布: 有 HIGH/MEDIUM/LOW/CRITICAL 各 ≥ 5%
- Agent 分布: 5 个 Agent 都有流量

---

## 需求 2: Dashboard 启动脚本

### 实现指引

- 文件: `scripts/run_dashboard.py`（新建）
- 或在 `pyproject.toml` 添加 entry point

```python
# scripts/run_dashboard.py
"""启动 TicketPilot Dashboard"""
import subprocess
import sys

def main():
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "src/ticketpilot/dashboard/app.py",
        "--server.port", "8501",
        "--server.headless", "true",
    ])

if __name__ == "__main__":
    main()
```

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python scripts/run_dashboard.py &
sleep 3
curl -s http://localhost:8501/_stcore/health
kill %1
```

期望: 返回 `ok`

---

## 需求 3: A/B 阈值调优实验

### 背景

A/B 实验框架已实现（`ticketpilot.experiment`），但从未实际跑过实验。当前置信度阈值是 HIGH≥0.78, MEDIUM≥0.6, LOW≥0.4，这组值是拍脑袋定的。

### 产品决策

跑一次 A/B 实验，对比两组阈值：
- **A组（当前）**: HIGH≥0.78, MEDIUM≥0.6, LOW≥0.4
- **B组（宽松）**: HIGH≥0.85, MEDIUM≥0.65, LOW≥0.45

评估指标：
- 自动发送率（HIGH+MEDIUM 的比例）— 越高越高效
- 人工审核触发率（LOW 的比例）— 越低越好（但不能太低）
- 风险漏报率（CRITICAL 中有 high risk 的比例）— 必须为 0

### 实现指引

- 文件: `scripts/run_threshold_ab.py`（新建）
- 使用现有 `ticketpilot.experiment.ab_runner` 模块

```python
from ticketpilot.experiment.config import ExperimentConfig, VariantConfig
from ticketpilot.experiment.runner import run_experiment

config = ExperimentConfig(
    name="threshold_tuning_v1",
    description="对比两组置信度阈值",
    variants=[
        VariantConfig(
            name="current",
            description="HIGH≥0.78, MEDIUM≥0.6, LOW≥0.4",
            params={"confidence_high": 0.78, "confidence_medium": 0.6, "confidence_low": 0.4},
        ),
        VariantConfig(
            name="strict",
            description="HIGH≥0.85, MEDIUM≥0.65, LOW≥0.45",
            params={"confidence_high": 0.85, "confidence_medium": 0.65, "confidence_low": 0.45},
        ),
    ],
    eval_tickets_path="data/eval/tickets_eval.csv",
)

report = run_experiment(config)
# 输出两组的 auto_send_rate, review_rate, risk_miss_rate
```

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python scripts/run_threshold_ab.py 2>&1 | grep -E "Variant|auto_send|review|risk_miss" -A 3
```

期望输出:
```
Variant: current
  auto_send_rate: XX%
  review_rate: XX%
  risk_miss_rate: 0%

Variant: strict
  auto_send_rate: XX%
  review_rate: XX%
  risk_miss_rate: 0%
```

两个 variant 的 risk_miss_rate 都必须为 0%。

---

## 全局验收 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate

# 1. Dashboard 数据验证
python3 -c "
from ticketpilot.dashboard.metrics_page import run_pipeline_on_eval_tickets
results = run_pipeline_on_eval_tickets()
assert len(results) == 101
print('✅ Dashboard 数据就绪')
"

# 2. A/B 实验验证
python scripts/run_threshold_ab.py > /tmp/ab_report.txt 2>&1
grep -q "risk_miss_rate: 0%" /tmp/ab_report.txt && echo "✅ 风险漏报为0" || echo "❌ 存在风险漏报"

# 3. 全量测试
python -m pytest --tb=no -q 2>&1 | tail -3
```

期望:
- Dashboard 数据: 101 张工单
- A/B 实验: risk_miss_rate = 0%
- 全量测试: 1644+ passed, 0 failed

最后 commit:
```bash
git add -A && git commit -m "feat: confidence dashboard + A/B threshold experiment"
```

---

## 约束

1. Dashboard 使用现有 Streamlit 框架，不引入新前端框架
2. A/B 实验使用现有 experiment 模块，不重写
3. 所有现有测试继续通过
4. Dashboard 不改变 Pipeline 逻辑
