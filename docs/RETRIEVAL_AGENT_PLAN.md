# TicketPilot 检索 + Agent 优化方案

**日期：** 2026-06-01
**当前状态：** 72 条知识，对抗评测 0.592，关键词+embedding 混合检索

---

## 一、问题诊断

### 1.1 证据检索评分低（0.016）

根因排序：
1. **Chunking 太粗** — 每条知识作为一整个 chunk（100-500字），检索时整块匹配，相关性被稀释
2. **关键词+embedding 未融合** — 关键词找到了但 embedding 分数低，RRF 融合后关键词结果被拉低
3. **embedding 模型局限** — bge-small 在短文本上区分度不够

### 1.2 系统不是 Agent

当前是确定性管线，没有：
- 自主决策能力（不能决定"要不要再搜一轮"）
- 工具调用能力（不能查物流、查订单）
- 多步推理能力（不能"先分析再行动"）

---

## 二、优化方案

### 2.1 Chunking 策略改造

**现状：** 每条知识 = 1 个 chunk（整块存储）

**目标：** 智能分块，保持语义完整

```
改造前：
  knowledge_chunks: [整块FAQ 300字] → embedding(300字) → 匹配困难

改造后：
  knowledge_chunks: 
    [标题+核心答案 50字] → embedding(50字) → 精准匹配
    [详细说明 150字]   → embedding(150字) → 补充上下文
    [相关条款 100字]   → embedding(100字) → 政策引用
```

**具体做法：**
1. 标题+首句 作为 parent chunk（高权重）
2. 详细内容 按段落拆分为 child chunks
3. 检索时先匹配 parent，再展开 children
4. 保持 source_table/source_id 引用链

### 2.2 RRF 权重调优

**现状：** 关键词和 embedding 等权重融合

**目标：** 关键词优先（中文短文本关键词匹配更可靠）

```
改造前：RRF(k=60), keyword weight = 1.0, embedding weight = 1.0
改造后：RRF(k=60), keyword weight = 1.5, embedding weight = 0.8
```

### 2.3 Agent 化改造

**架构：** 在 draft generation 前加一个 Agent 层

```
用户消息
  ↓
Pipeline (intake → classify → risk)
  ↓
DraftAgent (新增)
  ├── Step 1: 初次检索 (hybrid_retrieval)
  ├── Step 2: 评估证据质量
  │   ├── 证据充分 → 直接生成回复
  │   └── 证据不足 → 决定补充策略
  │       ├── 再搜一轮（换关键词/扩大范围）
  │       ├── 调用工具（查物流/查订单/查关税计算器）
  │       └── 标记为"需人工处理"
  ├── Step 3: 生成回复
  └── Step 4: 自检（回复是否基于证据、是否有幻觉）
```

**实现方式：** 用 DeepSeek 做 Agent 大脑，定义工具集：
- `search_knowledge(query)` — 检索知识库
- `calculate_tariff(amount, category)` — 计算关税
- `check_logistics(tracking_no)` — 查物流状态
- `escalate_to_human(reason)` — 转人工

### 2.4 Embedding 模型（可选升级）

bge-large-zh 只比 small 好 2%，性价比不高。
如果要升级，建议直接上 **bge-m3**（多语言，支持中英文混合查询，对跨境电商场景更合适）。

---

## 三、执行优先级

| # | 任务 | 预计收益 | 工作量 | 优先级 |
|---|------|---------|--------|--------|
| 1 | Chunking 拆分 | 证据检索 +30% | 2h | P0 |
| 2 | RRF 权重调优 | 检索融合 +15% | 30min | P0 |
| 3 | Agent 化改造 | 回复质量 +20% | 4h | P1 |
| 4 | Embedding 升级 | 匹配精度 +5% | 1h | P2 |

---

## 四、验收标准

- [ ] 证据检索评分 ≥ 0.3（当前 0.016）
- [ ] 对抗评测总分 ≥ 0.70（当前 0.592）
- [ ] Agent 能自主决定是否需要补充检索
- [ ] Agent 能调用工具（至少 search_knowledge）
