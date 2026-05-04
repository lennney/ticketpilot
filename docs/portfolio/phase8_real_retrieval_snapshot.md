# TicketPilot Phase 8 — Real Retrieval Upgrade Snapshot

> 作品集参考 · AI 产品方向
>
> 本文档记录 Phase 8 在固定 Phase 7 数据集下完成 fake vs real embedding retrieval comparison 的过程、指标、错例分析和产品判断。
>
> GitHub：<https://github.com/lennney/ticketpilot>

---

## 1. One-line Summary

Phase 8 在固定 Phase 7 数据集和 95 条知识库的前提下，引入真实中文 embedding provider，对比 fake embedding（384-d 确定性哈希）与 real embedding（DashScope text-embedding-v4, 1024-d）的检索排序效果。结果显示 real embedding 能改善 evidence ranking（Top-1 +10.9%，MRR +0.0799），但错例分析显示 41 个 wrong cases 在 fake 和 real 中完全一致，全部为 missing_doc_type —— 当前主要瓶颈是知识库覆盖，而不是单纯 embedding 质量。

---

## 2. Why This Phase Matters

客服 Copilot 的核心不是"模型会聊天"，而是证据检索是否命中、排序是否更合理、是否能被离线评测解释。Phase 8 的设计原则：

- **不是盲目换模型**，而是用固定 evaluation set 检查真实 embedding 是否改善 evidence retrieval。
- 保持 Phase 7 的 **101 eval tickets、101 golden expectations、95 knowledge chunks** 不变，避免对比被数据集变化污染。
- 对比结果不是为了证明"真实 embedding 更好"，而是为了判断：**下一步应该继续优化 embedding，还是转向知识库覆盖**。
- 评测结果指向后者——这比单纯报一个更高准确率更有产品决策价值。

---

## 3. Provider and Baseline Design

### Provider Architecture

Phase 8 设计了可切换的双 Provider 架构：

| Provider | 类型 | 维度 | 用途 |
|---|---|---|---|
| FakeEmbeddingProvider | 确定性 SHA-256 哈希 | 384-d | 默认 provider，用于 pipeline mechanics 验证、单元测试、baseline 对比 |
| OpenAICompatibleEmbeddingProvider | OpenAI-compatible HTTP API | 可配置（推荐 1024-d） | 真实中文 embedding，opt-in 切换 |

FakeEmbeddingProvider 是默认 provider，不依赖网络和 API key。Real provider 仅在本地通过环境变量 opt-in。

### Real Provider 配置示例

```bash
# .env.local (gitignored, 不提交到仓库)
EMBEDDING_PROVIDER=openai_compatible
EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EMBEDDING_MODEL=text-embedding-v4
EMBEDDING_DIM=1024
EMBEDDING_BATCH_SIZE=10
EMBEDDING_API_KEY=your_local_key_here
```

**安全约束：**
- API key 只允许放入 shell environment 或 `.env.local`
- `.env.local` 已在 `.gitignore` 中，不允许提交
- 所有 committed 代码中不包含真实 API key

### 推荐 Provider 选型

本次对比使用 **DashScope text-embedding-v4**（阿里云通义千问 embedding 服务），原因：
- 中文 embedding 质量在同类开源评测中表现稳定
- OpenAI-compatible API 格式，与代码库的 `OpenAICompatibleEmbeddingProvider` 兼容
- 1024-d 在精度和性能间取得合理平衡

其他 OpenAI-compatible provider（如 OpenAI text-embedding-3-small、BGE、text2vec）也可通过相同接口接入，只需修改 base_url、model、dimension。

---

## 4. Index Rebuild and Dimension Safety

Phase 8 的底层能力建设：

| 模块 | 功能 |
|---|---|
| `EmbeddingConfig` | 从环境变量加载 provider/model/dimension/batch_size，支持 CLI 覆盖 |
| `create_embedding_provider()` | Provider factory，按 provider 名称分发 |
| `OpenAICompatibleEmbeddingProvider` | HTTP client + Bearer auth + batch embedding，含 mocked unit tests |
| `scripts/rebuild_embeddings.py` | 完整重建 CLI：dry-run → 检查 metadata → 检查 dimension → 重建 → 写 metadata |
| `embedding_index_metadata` | 记录 provider、model、dimension、built_at、config fingerprint |
| `_alter_vector_dimension()` | NULL embeddings → ALTER COLUMN → 重建 HNSW index，安全应对 dimension 变更 |

**关键设计决策：**

- **Dimension mismatch 失败 loudly**：DB dimension 与 config dimension 不一致时，除非显式传入 `--allow-dimension-reset`，否则拒绝执行。
- **Fake 重建确认**：`rebuild_embeddings.py --confirm` 可在默认 fake provider 下重建，保证测试环境可恢复。
- **对比保持 95 chunks 不变**：Phase 8 没有修改 chunking 逻辑，fake vs real 对比只重建 embeddings，对比更干净。
- **DB 恢复**：完成 real provider 导出后，DB 已恢复 fake-384，正常开发不依赖真实 provider。
- **无 API key committed**：安全检查通过，committed 文件中无 secret 泄漏。

---

## 5. Offline Retrieval Comparison Results

### 指标表

| Metric | Fake 384-d | Real text-embedding-v4 | Delta |
|---|---:|---:|---:|
| Top-1 hit rate | 31.7% | 42.6% | **+10.9%** |
| Top-3 hit rate | 47.5% | 56.4% | **+8.9%** |
| Top-5 hit rate | 53.5% | 58.4% | **+5.0%** |
| Top-10 hit rate | 59.4% | 59.4% | 0.0% |
| MRR | 0.4114 | 0.4913 | **+0.0799** |
| Wrong cases | 41 | 41 | 0 |

### 指标解读

- **Top-1 / Top-3 / Top-5 / MRR 明显改善**：说明 real embedding 的语义匹配能力确实提升了证据排序质量。最相关的文档更容易出现在前三名。
- **Top-10 不变（同为 59.4%）**：说明当知识库中没有匹配内容时，更好的 embedding 也无法无中生有。Top-10 是当前知识库覆盖的 ceiling。
- **Wrong cases 不变（同为 41）**：说明这 41 个错例不是 embedding 质量能解决的。
- **结论**：real embedding **improves ranking under fixed offline evaluation**，但不能被包装成"真实 embedding 解决了检索问题"。

### 评测边界

- 本次评估是 **offline evaluation**，使用 101 条合成工单和固定 golden expectations，不是线上 A/B test。
- 数据为合成数据，不代表真实业务分布。
- 指标反映的是固定数据集下的相对排序改进，不能外推为生产级效果。

---

## 6. Wrong-case Analysis

### 核心发现

- **fake 和 real 的 41 个 wrong cases 完全相同**。
- **全部 wrong cases 归因为 missing_doc_type**：至少一种预期文档类型未出现在 Top-10 结果中。
- 没有任何 wrong case 属于 below_top_10（文档类型命中但排名低于 10）—— 说明当正确文档类型出现时，它总是在 Top-10 内。

### 按意图分布

| Intent | Wrong Cases | Total Cases | % of Intent |
|---|---|---|---|
| complaint | 10 | 13 | 77% |
| refund | 8 | 16 | 50% |
| return | 5 | 11 | 45% |
| account | 5 | 15 | 33% |
| logistics | 4 | 11 | 36% |
| other | 4 | 13 | 31% |
| edge | 5 | 5 | 100% |

### 错例分类

1. **空检索（4 cases）**：查询未能返回任何文档。其中 3 条在 golden 中预期文档类型也为空，属于标注不完整。
2. **预期类型缺失（37 cases）**：检索到部分正确类型但缺少至少一种。real embedding 改善的是已命中类型的排序，但无法补全缺失类型。
3. **No below_top_10**：所有命中类型都在 Top-10 内，没有"类型对了但排名太低"的情况。

### 产品判断

> Real embedding 改善 evidence ranking，但不能修复知识库覆盖缺口。当前上限主要是 knowledge base coverage，不是 embedding quality。

---

## 7. Product Manager Interpretation

### 不是"换模型就完事"

Phase 8 最重要的输出不是 "Top-1 提升了 10.9%"，而是 **通过 wrong-case analysis 定位到当前瓶颈**。

如果只看 Top-1 指标，结论可能是"真实 embedding 有用，继续换更好的模型"。但错例分析揭示了一个更结构性的结论：

> **41 个错例中没有一个能被 embedding 改善解决。下一步不是堆模型，而是补知识覆盖。**

### 这对客服 Copilot 意味着什么

客服 Copilot 的可信度不来自模型自由发挥，而来自以下几个可验证的能力：

| 层 | 能力 | 状态 |
|---|---|---|
| 证据命中 | 检索是否找到相关政策/案例 | Top-10 59.4%，受限于知识库覆盖 |
| 风险门控 | 是否识别投诉/法律/隐私风险 | 8 种标记 + 3 级严重度 |
| 证据引用 | 每项声明是否有引用支持 | Unsupported-claim guard |
| 人工审核 | 高风险/低置信度是否强制人审 | 所有风险标记触发 |
| 无自动发送 | 系统是否会被误用于直接回复 | 架构约束，不连接发送通道 |

Phase 8 的贡献是明确指出了 **证据命中这一层的当前瓶颈是知识覆盖而非排序模型**，为下一步迭代提供了方向。

### 下一步建议

1. **扩充知识库**：针对 missing_doc_type 的 41 个错例，补充对应 FAQ、Policy、Case 文档。
2. **增加 doc-level golden labels**：当前 golden 只有 doc type 级别的标注，增加 `expected_relevant_doc_ids` 可以支持更精细的 Recall@K 计算。
3. **扩展错例分析维度**：当前的 missing_doc_type / below_top_10 分类可以进一步细分（如"查询构建不当"、"知识域缺失"、"标注不一致"）。

---

## 8. Portfolio Boundary Statement

- **This is a local demo / portfolio prototype.** It is not a production-ready customer support system.
- **It does not use real enterprise customer data.** All tickets, knowledge records, and golden expectations are synthetic, manually adapted, or public-source-inspired.
- **The evaluation is offline evaluation**, not online A/B testing. Results reflect relative ranking improvement under a fixed dataset, not production benchmark.
- **The system is draft-only and human-in-the-loop.** It does not connect to any send channel. All outputs are drafts requiring human review before any action.
- **Real embedding results should be interpreted as ranking improvement under a fixed offline evaluation**, not as "semantic retrieval quality fully validated."
- **Fake embedding** is the default provider and validates pipeline mechanics only. Cosine similarity with fake embeddings has no semantic meaning.
- **No API key is committed** to the repository. The real provider is opt-in via local environment variables only.

---

## 9. Resume Bullets

以下为面向 AI 产品 / AI 产品经理方向的简历条目：

1. 设计并迭代 TicketPilot —— 中文电商售后工单 Copilot，覆盖工单分诊、意图分类、8 维风险识别、FAQ/Policy/Case 三层知识检索、证据化草稿与人工审核流程，定位为 draft-only human-in-the-loop local demo。

2. 构建 101 条合成中文客服工单和 101 条 golden expectations 评测集，及 95 条 FAQ/Policy/Case 三层知识库，支持 pipeline-backed offline evaluation 与错例分析。

3. 在固定数据集下完成 FakeEmbeddingProvider（384-d）与 DashScope text-embedding-v4（1024-d）的 retrieval ranking 对比，Top-1 hit rate 从 31.7% 提升至 42.6%，MRR 从 0.4114 提升至 0.4913。

4. 基于 wrong-case analysis 发现 41 个错例（fake 与 real 完全相同）均为 missing_doc_type，判断当前主要瓶颈由模型排序转向知识库覆盖，为后续知识补全和评测标签优化提供依据 —— 而非单纯"换模型提高准确率"。

5. 为非功能性质量设计分级 validation policy：docs-only 内容审查、OpenSpec scoped `--strict` 验证、全量 quality gate（pytest 760 unit + 119 integration + 85% coverage + ruff + secret scan）三层检查体系。

6. 通过 OpenSpec spec-driven development、pytest、Ruff、coverage gate、secret scan 和分级 validation policy 管理 AI 协作开发质量，避免 demo 只停留在 UI 展示。

---

## 10. Interview Talking Points

### 1-Minute Version

"TicketPilot 是一个中文电商售后工单 Copilot 原型。用户提交一条客服消息，系统做意图分类、风险识别、分层知识检索，然后生成带证据引用的回复草稿，高风险工单强制人工审核。它不是全自动客服，不做 LLM，不自动发送。

Phase 8 的核心是：在固定 101 条评测数据下，对比 fake embedding 和真实中文 embedding（DashScope text-embedding-v4）的检索排序。结果显示真实 embedding 让 Top-1 从 31.7% 提升到 42.6%，MRR 也从 0.41 提升到 0.49。

但更有意思的是错例分析：fake 和 real 有完全相同的 41 个 wrong cases，全部是 missing_doc_type。这说明当前主要瓶颈不是 embedding 质量，而是知识库覆盖。这个结论让我决定下一步不是继续换模型，而是补知识、加 doc-level 标注。"

### 3-Minute Version

"TicketPilot 是一个面向中文电商售后场景的工单 Copilot 原型。它解决的核心问题是：客服工单处理过程中，意图判断不统一、风险容易被遗漏、回复质量依赖个人经验。

我们的设计选择是不做全自动客服机器人，而是做一个 draft-only human-in-the-loop 的 AI 辅助决策系统。具体来说：用户提交消息 → 系统做意图分类（8 类确定性规则）→ 风险识别（8 种标记 + 3 级严重度）→ FAQ/Policy/Case 三层知识检索 → 生成带证据引用的回复草稿 → 高风险工单强制人工审核。系统不连接任何发送通道，所有输出只是草稿。

项目从 Phase 1 到 Phase 7，建立了 101 条合成工单的评测集、101 条 golden expectations、95 条知识记录，以及 Pipeline 和 CSV 两种评测模式。

Phase 8 的目标是：在固定数据集下，看看真实中文 embedding 到底能不能改善证据检索排序。我们保持了 95 条 chunks 完全不变，只切换 embedding provider。

结果很有趣：
- 真实 embedding 确实改善了排序：Top-1 从 31.7% 升到 42.6%，MRR 从 0.41 升到 0.49。
- 但 Top-10 命中率停在 59.4%，wrong case 数量也没变——同样是 41 个。

我们做了错例分析，发现这 41 个错例全部是 missing_doc_type，且 fake 和 real 完全一致。也就是说，当前系统能不能找到对的知识，瓶颈不在 embedding，而在知识库本身有没有覆盖这些场景。

这个判断比单纯的"准确率提升了 X%"更重要。因为它指明了下一步方向：不是继续换更好的 embedding 模型，而是针对这 41 个错例补充知识库，同时增加 doc-level 的 golden labels，让评测能细化到具体文档级别。

对我来说，这次迭代最有价值的部分不是指标提升本身，而是通过评测和错例分析，把"模型能不能做得更好"的问题转换成了"知识库覆盖是否足够"的产品判断——这比堆模型更接近真实的产品迭代逻辑。"

---

> *本文档基于 TicketPilot Phase 8 Real Retrieval Upgrade，在 Phase 7 MVP Evidence Pack 基础上完成 embedding provider 切换与检索对比评测。*
>
> *编写日期：2026-05-05*
