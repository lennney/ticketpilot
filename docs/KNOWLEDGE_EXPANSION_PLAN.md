# TicketPilot 知识库扩展 + 检索优化计划

**日期：** 2026-06-01
**当前状态：** 36 条跨境电商知识，对抗评测 0.577/1.0
**目标：** 200+ 条知识，评测 0.75+

---

## 一、知识库扩展

### 1.1 数据来源（优先级排序）

| # | 来源 | URL | 工具 | 预计条目 | 优先级 |
|---|------|-----|------|---------|--------|
| 1 | JD 国际帮助中心 | help.jd.com (跨境/海囤全球) | fetch.py | 40-60 | P0 |
| 2 | 天猫国际规则 | rule.taobao.com + tmall.hk | fetch.py | 30-50 | P0 |
| 3 | 拼多多海外购 | mms.pinduoduo.com/other/help | fetch.py | 20-30 | P1 |
| 4 | 速卖通卖家中心 | sell.aliexpress.com/zh | fetch.py | 20-30 | P1 |
| 5 | 海关总署政策 | customs.gov.cn | fetch.py | 15-20 | P1 |
| 6 | 12315 投诉标准 | 12315.cn | fetch.py | 10-15 | P2 |
| 7 | 消费者权益保护法 | gov.cn 政策库 | fetch.py | 10-15 | P2 |
| 8 | 天池 JD 客服对话 | tianchi.aliyun.com | 手动下载 | 100+ | P2 |

### 1.2 爬取流程

```
1. ddgs 搜索 → 找到具体政策页面 URL
2. fetch.py 抓取 → 转 markdown
3. LLM 结构化 → 提取 FAQ/Policy/Case 条目
4. 写入 PostgreSQL → knowledge_faq/policy/case + knowledge_chunks
5. 重建 BGE embedding
```

### 1.3 质量控制

- 每条知识必须有明确来源 URL
- FAQ 覆盖：海关、物流、退换货、支付、账号、合规
- Policy 覆盖：税收、监管、消费者保护、平台服务承诺
- Case 覆盖：真实场景复现（纠纷、投诉、赔偿）

---

## 二、检索优化（第二阶段）

### 2.1 当前问题

纯 embedding 检索，BGE-small-zh-v1.5 的语义匹配在短文本上效果差。
对抗评测 evidence_retrieval = 0.016，几乎没命中。

### 2.2 优化方案

**混合检索（Hybrid Retrieval）：**
- **BM25 关键词匹配** — 对中文短文本效果好，精确匹配
- **Embedding 语义匹配** — 捕获语义相似但措辞不同的查询
- **RRF 融合** — 已有实现，需要调权重

**具体改动：**
1. `keyword_search.py` — 检查当前 FTS 实现，确保中文分词正常
2. `vector_search.py` — embedding 匹配阈值调低（当前太严格）
3. `rrf.py` — 调整 BM25 vs embedding 权重（建议 6:4）

---

## 三、执行计划

| 阶段 | 任务 | 负责 | 预计时间 |
|------|------|------|---------|
| Phase 1 | 爬取 JD/天猫/海关政策 | Agent A | 30 min |
| Phase 2 | LLM 结构化 + 入库 | Agent B | 20 min |
| Phase 3 | 重建 embedding | 自动 | 5 min |
| Phase 4 | 对抗评测 v3 | 自动 | 5 min |
| Phase 5 | 检索优化 | Agent C | 30 min |
| Phase 6 | 最终评测 v4 | 自动 | 5 min |

---

## 四、验收标准

- [ ] 知识库 ≥ 200 条（FAQ + Policy + Case）
- [ ] 对抗评测总分 ≥ 0.75
- [ ] 证据检索评分 ≥ 0.3（当前 0.016）
- [ ] 意图分类准确率 ≥ 0.7
- [ ] 风险识别召回 ≥ 0.8
