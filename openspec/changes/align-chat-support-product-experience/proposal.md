# Proposal: Align Chat Support Product Experience

## 当前问题

TicketPilot 的底层能力已较完整：意图分类、风险评估、分层知识检索、证据驱动草稿生成、引用验证、claim guard、人工审核控制台、离线评测。但近期迭代（Phase 13–14）逐渐偏向 guard taxonomy 内部工程细节，产品形态描述为"工单分诊与证据化回复 Copilot"或"guard architecture"，偏离了最初的愿景。

## 用户最初的愿景

一个类似淘宝/京东客服场景的 AI 客服系统：

1. 用户在聊天窗口向 AI 客服提问
2. AI 先接待并识别问题类型
3. 普通 FAQ / 售后政策问题 → 生成证据化客服回复草稿
4. 检测到退款争议、投诉、赔偿、隐私、法律、账号安全、证据不足 → 触发人工介入
5. 后台人工客服看到：用户问题、issue_type、risk_flags、severity、retrieved evidence、AI draft、guard result，然后 Approve / Edit / Escalate / Reject

## 重新对齐后的产品定位

**TicketPilot = 面向中文电商/售后客服场景的 AI 客服 Copilot（本地 demo）**

核心叙事：

- 前台：模拟用户与 AI 客服对话的聊天体验
- 后台：人工客服接管审核台
- 机制：风险自动识别，高风险转人工，不自动回复
- 底座：证据化回复 + claim guard 作为安全约束

### 与当前的差异

| 维度 | 当前叙事 | 目标叙事 |
|---|---|---|
| 产品形态 | 工单分诊 + guard architecture | 电商 AI 客服 Copilot |
| 用户视角 | 内部 Copilot | 用户可见的聊天体验 |
| 叙事焦点 | taxonomy / citation / guard | 聊天体验 / 风险流程 / 人工介入 |
| 演示重点 | 底层 pipeline | 前台 chat + 后台 review |

### 已有的能力映射

- `intent classification` → chat 中的问题类型识别
- `risk detection` → chat 中触发人工介入的信号
- `FAQ / Policy / Case retrieval` → chat 中展示证据
- `draft generation` → chat 中 AI 客服回复草稿
- `citation validation` → 草稿中证据引用的合规性
- `claim guard` → 安全底座，不允许有问题的草稿通过
- `human review console` → 后台人工客服接管台
- `offline evaluation` → 评测 chat + review 的端到端效果

### 不需要新增的

- 新增 LLM 能力（已有）
- 新增检索能力（已有）
- 新增 guard 能力（已有）
- 新增 review console（已有）

### 需要做的

1. **产品叙事重新对齐**：将整个项目描述为 AI 客服 Copilot，而不是 guard architecture
2. **前台 chat demo**：Streamlit chat-style UI，展示用户对话、AI 草稿、风险状态
3. **Pipeline-to-chat adapter**：把现有 pipeline 输出适配到 chat UI
4. **证据展示面板**：chat 中展示检索到的证据
5. **风险状态展示**：chat 中展示 risk_flags / severity / human intervention status
6. **Human review 联动**：高风险 → 进人工队列

## MVP Scope（第一阶段）

优先 Streamlit chat demo，不引入 React / Next.js：

- 用户在 chat input 输入消息
- 系统展示 AI 客服回复草稿
- 展示是否触发人工介入
- 展示风险原因和证据
- 高风险不允许模拟自动回复
- 使用 FakeLLMProvider，不调用真实 API

## Non-Goals

- 不做 production-ready 系统
- 不接真实发送通道
- 不使用真实客户数据
- 不做真实 LLM 对比
- 不做 guard taxonomy 扩展（Phase 14 已完成的保留）

## Boundary

- **Local demo / portfolio prototype** — 不是生产级系统
- **Synthetic data only** — 101 条合成工单 + 106 条知识记录
- **No real customer data** — 所有数据是模拟的
- **No auto-send** — 草稿不自动发给用户
- **Human-in-the-loop** — 高风险强制人工审核
- **Offline evaluation** — 评测基于离线 fixture，不做线上 A/B

## 影响评估

- README.md / portfolio docs 需要更新产品叙事
- Phase 14 guard taxonomy 工作继续有效，只是叙事优先级调整
- Phase 15 后续任务将聚焦 chat demo 而非 guard 扩展
