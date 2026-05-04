# TicketPilot Limitations

> 当前版本（Phase 7 MVP Evidence Pack）的已知限制和范围边界。
> 本文件适用于作品集评估、面试提问和后续开发参考。

---

## 1. Project Maturity

- **Local demo / portfolio prototype** — TicketPilot 是一个架构优先的功能演示项目，不是生产级客服系统。
- 不适用于生产环境、真实客服工作流或企业级部署。
- 未经过安全审计、负载测试或合规审查。

## 2. Data

- **所有工单数据均为合成（synthetic）**：Phase 7 的 101 条 eval tickets 是手动编写的中文客服场景，不是真实企业客户数据。
- **知识库为合成 / 手工改编**：95 条知识记录（FAQ=40, Policy=30, Case=25）基于常见电商客服场景编写，不来源于任何真实企业的知识库、工单系统或政策文档。
- **Topic 分布偏向评测场景**：知识库覆盖面向 101 条 eval tickets 的场景，不代表真实业务分布。
- **无真实企业数据**：系统不包含、不使用任何真实企业的客户数据、工单记录或政策文件。

## 3. Embedding & Retrieval

- **Fake embedding（确定性哈希）**：默认使用 FakeEmbeddingProvider，生成 384 维确定性 SHA-256 哈希向量。余弦相似度分数无语义含义，仅验证管道机械正确性（pipeline mechanics）。
- **无语义检索质量**：当前向量检索不能证明语义理解能力。关键词全文搜索（FTS）是主要检索手段。
- **Phase 8 才做真实中文 embedding 对比**：真实嵌入服务（如 text2vec、BGE）的集成和检索质量评估已规划但未开始。

## 4. Draft Generation

- **无真实 LLM**：草稿生成使用确定性模板（FakeDraftProvider），不调用任何 LLM API。
- **模板生成**：草稿质量受限于预定义模板的质量，不是生产级回复质量。
- **不自动发送**：所有回复都是草稿，不连接任何发送通道。人工审核决策仅写入本地 JSONL 文件。

## 5. Evaluation

- **离线评测**：当前评估报告是离线确定性评测，不是线上 A/B test 或真实业务 benchmark。
- **小规模数据集**：101 条 tickts 和 95 条知识记录不足以支持统计显著性分析。
- **意图 / 严重度指标**：当前 pipeline mode 的 intent accuracy (~53%) 和 severity accuracy (~54%) 反映了 fake embedding 和基于规则的组件的行为。这些指标不能被包装成生产效果，只能说明评测体系已建立。
- **No-auto-send compliance = 100%**：这是架构约束（系统不连接发送通道），不是自动回复质量指标。
- **无真实用户验证**：未经过真实客服人员或终端用户验证。

## 6. UI & Review

- **Streamlit 控制台**：为 MVP 级别的人工审核界面，非生产前端。无身份验证、无多用户支持、无操作日志审计（仅 JSONL）。
- **无自动刷新**：控制台不自动刷新审核队列。

## 7. Architecture

- **无真实外部依赖**：所有外部服务（embedding、LLM）均有 fake 实现，确保管道可离线验证。
- **无消息队列**：系统同步运行，无异步任务队列。
- **无 Webhook 或 API**：系统不暴露任何外部 API 端点（除 Streamlit 本地界面外）。
- **PostgreSQL + pgvector**：需要本地 Docker 运行。无远程数据库支持。

## 8. What Phase 7 Does Cover

- 8 类意图分类（refund, return_exchange, account_issue, technical_issue, product_consulting, logistics, complaint, other）
- 8 种风险标记检测（complaint, compensation, legal, account_security, privacy, policy_conflict, insufficient_evidence, low_confidence）
- 分层检索：关键词 FTS + 向量 HNSW + RRF 融合（fake embeddings）
- 人工审核工作流：Approve / Edit / Escalate / Reject
- 离线评估流水线：CSV 模式和 pipeline 模式
- 确定性、可复现、无 LLM 依赖

## 9. Phase 8+ Roadmap (Deferred)

| 方向 | 说明 |
|------|------|
| 真实中文 embedding provider | text2vec / BGE 集成 + 检索质量评估 |
| 真实 LLM 草稿生成 | 可选的 LLM 驱动草稿生成器 |
| 真实数据包 | 基于公开数据源的扩展知识库和 eval 数据集 |
| 在线评估 | 请求级指标追踪和回归检测 |
| 生产化部署 | Docker 多服务编排、CI/CD、监控 |

---

> *TicketPilot — 本地演示 / 作品集项目。详见 [README.md](../README.md) 和 [changelog.md](../docs/changelog.md)。*
