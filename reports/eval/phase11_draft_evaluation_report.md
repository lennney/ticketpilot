# Phase 11.8 — Offline Draft Evaluation Report

> **评估时间:** 2026-05-06 11:14 UTC
> **数据来源:** data/eval/tickets_eval.csv
> **提供商:** FakeLLMProvider (确定性，无网络调用)

> **范围边界:**
> - 本地演示 / 作品集原型 — 不是生产系统
> - 合成数据 — 不使用真实客户数据
> - 离线评估 — 不是生产基准测试
> - 草稿生成模式 — 不自动发送回复
> - 无真实 LLM API 调用 — 使用确定性 FakeLLMProvider

## 指标定义

| 指标 | 定义 |
|---|---|
| citation_precision_avg | 有效引用数 / 总引用数 (无引用时为 None，不计入平均) |
| evidence_coverage_avg | 已引用有效证据数 / 可用证据数 (无可用证据时为 None，不计入平均) |
| unsupported_claim_rate | 含有无证据声明的案例数 / 总案例数 |
| forbidden_promise_rate | 检测到禁止承诺的案例数 / 总案例数 |
| safe_fallback_rate | 触发无证据回退的案例数 / 总案例数 |
| human_review_trigger_accuracy | 人工审核触发正确率 (期望 vs 实际) |
| citation_validation_pass_rate | 引用验证通过的案例数 / 总案例数 |
| claim_guard_pass_rate | 护卫检查通过的案例数 / 总案例数 |
| average_confidence | 平均置信度 (无置信度数据时为 None) |

## 汇总指标

| 指标 | 值 |
|---|---|
| 总案例数 | 10 |
| Citation Precision Avg | 1.0000 |
| Evidence Coverage Avg | 0.3000 |
| Unsupported Claim Rate | 0.4000 |
| Forbidden Promise Rate | 0.1000 |
| Safe Fallback Rate | 0.0000 |
| Human Review Trigger Accuracy | 0.6000 |
| Citation Validation Pass Rate | 0.6000 |
| Claim Guard Pass Rate | 0.0000 |
| Average Confidence | 0.0166 |

## 简短解读

共评估 10 个工单。
平均引用精确度为 100.00%，反映了草稿中引用的证据质量。
无证据支持的声明率为 40.00%，这些案例需要人工审核。
禁止承诺率为 10.00%，这些案例触发了安全护卫检查。

## 局限性说明

- **FakeLLMProvider 测试工作流机制，而非真实 LLM 生成质量**
- 无生产环境或企业级验证
- 无真实客户数据
- 仅使用离线合成fixture评估
- 下一阶段建议接入真实 LLM provider 以验证语义生成质量
