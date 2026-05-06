# TicketPilot 项目案例

## 项目背景

TicketPilot 是一个面向中文客服工单的智能分诊与证据溯源回复助手（Copilot）。项目从零开始，采用 OpenSpec 规范驱动开发模式，通过 11 个阶段的迭代逐步构建完成。

项目定位为 MVP（最小可行产品），核心目标是验证以下技术可行性：

- 中文客服工单的结构化处理（标准化、意图分类、风险评估）
- 基于混合检索（关键词 + 向量）的证据溯源知识库查询
- 证据溯源草稿回复生成（模板 / LLM 约束）
- 人工审核控制台（Human-in-the-Loop）
- 通过迭代评测确定下一步优化方向，而非盲目堆功能

## 业务问题

在线客服团队每天处理大量非结构化的中文工单。客服人员需要快速理解工单意图、评估风险等级、查阅相关知识库（FAQ、政策条款、历史案例），然后撰写回复。这一流程存在以下痛点：

1. **工单处理无标准化**：工单以自由文本形式到达，缺乏统一结构，无法自动化处理
2. **风险识别依赖个人经验**：退款纠纷、法律风险、隐私泄露等敏感工单依赖客服个人判断
3. **知识查找耗时**：客服需手动在 FAQ、政策文档和历史案例中搜索相关信息
4. **回复质量参差不齐**：缺乏证据溯源的回复容易产生不准确或误导性内容

TicketPilot 旨在通过自动化流水线解决上述问题，同时保留人工审核机制以控制风险。

## 用户场景与工作流

### 典型场景

某电商平台客服收到用户工单："我要退款，订单号是 12345，你们发的货是坏的，我要赔偿！"

### 系统处理流程

```
用户提交工单 → 标准化处理 → 意图分类 → 风险评估 → 知识检索 → 草稿生成(可选) → 人工审核
```

1. **标准化**：清洗文本、提取订单号（12345）和实体信息
2. **分类**：判定为 REFUND（退款）意图
3. **风险评估**：检测到"赔偿"关键词，触发 COMPENSATION_RISK（赔偿风险）标志
4. **知识检索**：根据退款意图 + 赔偿风险，从 FAQ/政策/案例库中检索相关条款和先例（106 条知识记录，混合检索 + RRF 融合）
5. **草稿生成**（可选）：基于检索到的证据，生成带引用的回复草稿；ClaimGuard 校验声明真实性和禁止承诺
6. **人工审核**：客服在审核控制台中查看草稿，可批准、编辑、升级或驳回

## 系统架构

### 六层架构

TicketPilot 采用模块化流水线架构，共 6 层（4 层核心 + 2 层可选）：

| 层级 | 功能 | 强制/可选 |
|------|------|-----------|
| Layer 1: 工单接入 | 文本标准化、实体提取（订单号、产品、金额） | 强制 |
| Layer 2: 意图分类 | 基于规则的 8 分类（退款、换货、投诉、账号问题等） | 强制 |
| Layer 3: 风险评估 | 8 个风险标志（赔偿、法律、隐私、账户安全等） | 强制 |
| Layer 4: 知识检索 | 混合检索（关键词 + 向量）+ RRF 融合 | 强制 |
| Layer 5: 草稿生成 | 模板 / LLM 证据约束生成（可切换 provider） | 可选 |
| Layer 6: 人工审核 | Streamlit 审核控制台，记录审核决策 | 可选 |

### 核心模块

| 模块 | 目录 | 说明 |
|------|------|------|
| 工单接入 | `src/ticketpilot/intake/` | 文本清洗、实体提取（正则匹配中国订单号、金额） |
| 意图分类 | `src/ticketpilot/classification/` | 基于字典关键词的规则分类器，8 个意图类别 |
| 风险评估 | `src/ticketpilot/risk/` | 8 个风险标志，含严重度计算和人工审核触发逻辑 |
| 知识检索 | `src/ticketpilot/retrieval/` | 混合检索引擎：PostgreSQL FTS + pgvector HNSW + RRF；支持 Fake 384-d 和 Real 1024-d 双 provider |
| 草稿生成 | `src/ticketpilot/drafting/` | 抽象提供者模式 + FakeDraftProvider/FakeLLMProvider + PromptBuilder + ClaimGuard |
| 人工审核 | `src/ticketpilot/review/` | ReviewDecision 审计模型 + ReviewStore JSONL 持久化 |
| 流水线编排 | `src/ticketpilot/pipeline.py` | 4 阶段流水线，每阶段独立 try/except 降级 |

### 技术栈

| 组件 | 技术 |
|------|------|
| 运行环境 | Python 3.11+ (uv 包管理) |
| 数据库 | PostgreSQL 16 + pgvector |
| 关键词检索 | PostgreSQL FTS (simple 配置 + GIN 索引) |
| 向量检索 | pgvector HNSW (m=16, ef_construction=200, ef_search=100, 余弦距离) |
| 排序融合 | RRF (k=60) |
| 真实嵌入（opt-in） | DashScope text-embedding-v4 (1024-d) |
| 数据建模 | Pydantic |
| 审核界面 | Streamlit (MVP 原型) |
| 开发模式 | OpenSpec 规范驱动开发 |
| 容器化 | Docker Compose |

## 项目迭代历程

TicketPilot 最核心的差异化不是功能堆叠，而是通过评测驱动的迭代决策。

### Phase 7: MVP 数据基底与评测体系

- 评测数据集从 10 条扩展到 **101 条合成工单**，覆盖全部 8 类意图和 8 种风险标记
- 知识库从 36 条扩展到 **95 条记录**（FAQ=40, Policy=30, Case=25），新增发票/支付领域
- 建立确定性离线评测流水线（CSV + Pipeline 双模式，7 项指标）
- 3 个强 demo 场景文档 + 完整限制说明

### Phase 8: 真实嵌入升级与检索对比

- 接入 DashScope text-embedding-v4（1024-d），保留 Fake 作为默认
- 在固定 Phase 7 数据集下完成对比评测
  - Top-1 hit rate: 31.7% → 42.6%（+10.9%）
  - MRR: 0.4114 → 0.4913（+0.0799）
- **关键发现**：fake 和 real 的 41 个 wrong cases 完全一致，全部为 missing_doc_type
- **产品判断**：当前瓶颈在知识库覆盖，不在 embedding 质量

### Phase 9: 评估驱动知识优化

- 41 个 wrong cases → 8 类故障分类法 → 24 个知识缺口映射
- 定向补充 **11 条 P0 知识记录**（总记录 95→106）
- **关键发现**：`load_dotenv()` 未被调用，所有评测静默回退到 fake provider
- 修复后 P0 hit rate 达 75.0%，Top-1 提升 2.0%
- **产品判断**：Provider Identity Gate 必须建立——不能相信你不知道来源的指标

### Phase 10: 检索排名诊断与细粒度评测

- doc-level golden labels 从 14 扩展到 **86 个评测用例**
- 评测单位从 doc_type 细化为 doc_id
- **Doc-ID Recall@10 = 91.9%**，较 doc-type 指标提升 32.5 个百分点
- **核心结论**：78% 的"错误"案例实为评测粒度问题，而非检索系统失效
- 识别 7 个 zero-hit 案例（query expansion 候选）和 32 个 partial-hit 案例（fusion ranking 候选）

### Phase 11: 证据约束 LLM 草稿生成（已完成）

- LLM provider 抽象接口 + FakeLLMProvider 确定性实现（无 API 依赖）
- Evidence-grounded prompt builder（证据约束 + 安全规则 + 输出格式规范）
- DraftCitationValidationResult 和 validate_draft_citations()
- ClaimGuard（5 层检查：声明覆盖率、无证据声明、禁止承诺、证据充足性、风险感知）
- DraftGenerationResult + generate_draft() 管线串联所有组件
- Human review console 更新（15 个审计字段 + guard 状态展示）
- 离线草稿评估指标（8 项确定性指标，引用精确度=100%，claim guard 通过率=0%）
- 8 层安全架构：prompt 约束 → 引用验证 → ClaimGuard → 风险感知 → 人审传播 → no-auto-send → fake 默认 → provider 追踪

### 迭代逻辑总结

```
Phase 7: 建数据基底和评测体系
  → Phase 8: 换真实嵌入，发现瓶颈在知识覆盖
    → Phase 9: 补知识，发现配置静默回退问题
      → Phase 10: 精细化评测，发现大部分"错误"是粒度问题
        → Phase 11: 完成证据约束草稿生成，构建 8 层安全架构（已完成）
```

## AI 工作流设计

### 混合检索设计

检索系统采用混合检索策略——关键词检索 + 向量检索——以克服单一检索方式的局限性：

- **关键词检索（PostgreSQL FTS）**：适合精确匹配政策编号（如"7.3.2"）、产品代码等。使用 `simple` 分词配置，搭配 8 个中文业务关键词的 LIKE 回退机制
- **向量检索（pgvector HNSW）**：适合语义相似的查询匹配。默认使用 FakeEmbeddingProvider（384-d）；可切换至 DashScope text-embedding-v4（1024-d，真实中文语义）
- **RRF 融合**：将两种检索结果按排名融合，k=60
- **真实嵌入对比**：Phase 8 完成，Top-1 +10.9%，MRR +0.0799，但瓶颈在知识覆盖而非 embedding

### 草稿生成设计

草稿生成采用可选工作流设计，不改变核心流水线的返回值约定：

- **双 provider 模式**：FakeDraftProvider（模板）+ FakeLLMProvider（证据约束 LLM），均为确定性实现
- **Evidence-grounded prompt builder**：将证据 + 安全规则 + 输出格式约束编译为结构化 prompt
- **CitationValidator + ClaimGuard**：引用校验 + 声明检测 + 禁止承诺检测
- **安全回退**：无证据时返回安全消息，高风险时标记 `must_human_review=True`

### 流水线完整性保障

- 每阶段均有 try/except 降级处理，流水线永不崩溃
- 检索阶段单独隔离，失败时返回空证据 + INSUFFICIENT_EVIDENCE 标志
- 不可变标志处理：`_with_added_risk_flag()` 辅助函数创建新对象而非修改原集合
- Provider Identity Gate：运行时验证实际使用的 provider，防止配置静默回退

## 人工审核设计

### 审核机制

人工审核是系统的安全核心，而非可选附加功能：

- **审核触发条件**：高风险标志、草稿未受支持声明、证据不足、ClaimGuard 校验失败
- **四种审核操作**：APPROVE（批准）、EDIT（编辑）、ESCALATE（升级）、REJECT（驳回）
- **审计追踪**：每条审核记录包含审核时的完整快照

### 安全约束

- **不自动发送回复**：审核控制台仅记录决策，无任何发送功能
- **审核决策持久化**：采用追加式 JSONL 文件存储
- **无认证机制**：审核员身份为自由文本标签，适用于本地 MVP 演示

## 质量标准与测试纪律

### 质量门禁

项目维护严格的自动化质量门禁脚本，包含 5 个阶段：

| 检查项 | 阈值 | 说明 |
|--------|------|------|
| Ruff 静态检查 | 0 错误 | 所有源文件和测试文件 |
| 单元测试 | 全部通过 | 覆盖率 >= 70% |
| 集成测试 | 全部通过，0 跳过 | 跳过计数守卫，DB 不可用时需显式绕过 |
| OpenSpec 验证 | 全部通过 | 验证规范与实现一致性 |
| 密钥扫描 | 0 个 | 扫描 OpenAI 格式密钥 |

### 测试度量（最新）

- **单元测试**：~856 个全部通过
- **集成测试**：119 个全部通过，0 跳过
- **代码覆盖率**：>70%（满足质量门禁阈值）

### 测试纪律

- 单元测试隔离数据库依赖（使用 mock），始终可运行
- 集成测试连接真实 PostgreSQL + pgvector，验证完整流水线
- 集成测试跳过计数守卫确保隐式跳过被捕获

## 当前演示能力

### 可演示内容

1. **端到端流水线**：从 `RawTicket` JSON 输入到完整 `TicketOutput`
2. **混合检索**：关键词 + 向量检索 + RRF 融合，含完整检索追踪
3. **草稿生成**：基于证据的回复草稿（模板 / FakeLLM + 引用标注）
4. **人工审核控制台**：Streamlit 界面展示完整审核工作流
5. **审核决策持久化**：追加式 JSONL 文件
6. **检索对比**：Fake vs Real embedding 离线对比指标
7. **细粒度检索评测**：Doc-ID Recall@10 = 91.9%

## 局限性

- **本地 Demo / 作品集原型**：不是生产级系统，未经安全审计或负载测试
- **合成数据**：101 条工单和 106 条知识记录均为合成
- **默认 Fake embeddings**：真实嵌入需通过环境变量 opt-in
- **草稿非生产级**：模板生成 / FakeLLM，不调用真实 LLM API
- **Draft-only / no auto-send**
- **离线评测**：非线上 A/B test
- **UI 级别**：Streamlit MVP，无身份验证/多用户

## 下一步计划

| 方向 | 优先级 |
|------|--------|
| Phase 11 收尾（LLM provider + ClaimGuard + 草稿评估） | ✅ 已完成 |
| 检索排序优化（query expansion / RRF 调参） | P0 |
| 真实数据包 | P1 |
| 扩展评测数据集 | P1 |
| LangGraph 工作流编排 | P2 |
