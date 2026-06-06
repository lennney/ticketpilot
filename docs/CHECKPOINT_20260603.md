# TicketPilot Checkpoint — 2026-06-03

## 当前状态

### 已完成的优化
1. **DB去重**: 1505 → 1002 chunks (删除503个重复child chunks)
2. **意图分类器优化**: 79.1% → 98.5% (rules.py关键词大幅扩展)
3. **RRF参数调整**: k=20→60, 去掉权重(等权融合)
4. **内容去重**: rrf_fusion中按content去重
5. **Domain filter恢复**: keyword_search/vector_search/pipeline全部支持exclude_business_domains
6. **Eval数据修正**: R003/G007等ground_truth修正
7. **知识补充**: 新增押金退款policy chunk

### 关键文件改动
- `src/ticketpilot/classification/rules.py` — 意图关键词扩展(98.5%准确率)
- `src/ticketpilot/retrieval/rrf.py` — RRF_K=60, 内容去重
- `src/ticketpilot/retrieval/pipeline.py` — exclude_business_domains参数
- `src/ticketpilot/retrieval/keyword_search.py` — domain filter支持
- `src/ticketpilot/retrieval/vector_search.py` — domain filter支持
- `data/eval/agent_eval_dataset_v2.json` — GT修正
- `data/knowledge/policy_seed.json` — 新增押金policy
- `scripts/dedup_chunks.py` — 去重脚本

### Eval基线对比

| 指标 | 旧(修复前) | 新(修复后) | 目标 |
|------|-----------|-----------|------|
| Intent | 79.1% | 98.5% | ≥95% ✓ |
| Faithfulness | 0.962 | 0.957 | ≥0.95 ✓ |
| Relevancy | 0.906 | 0.910 | ≥0.90 ✓ |
| Precision | 0.532 | 待重跑 | ≥0.85 |
| Recall | 0.593 | 待重跑 | ≥0.80 |
| Pass Rate | 31.3% | 待重跑 | - |

### ⚠️ 注意事项
- **子任务会回退修改!** delegate_task的子任务可能回退之前的手动修改。下次做检索优化时要自己直接改，不要委托子任务。
- DashScope embedding用OpenAI SDK调用（requests库有SSL问题）
- DeepEval judge用DeepSeek，分批20条避免超时

## 待做 (明天继续)

### P0: 重跑eval
- eval正在后台跑 (proc_818b291ef2ae)，等结果出来看precision/recall变化
- 如果precision没提升，需要进一步优化检索

### P1: 检索进一步优化
- **DashScope reranker API**: 用gte-rerank-v2替代当前的embedding similarity reranker
- **增加top_k**: 从5增加到8-10，给LLM更多context
- **改进query expansion**: 对短query做关键词扩展

### P2: 知识库补充
- 补充"超过7天质量退款"的30天时限政策 (R001)
- 补充"升级投诉"相关知识 (C009)
- 补充"验证码"相关技术知识 (T006)

### P3: 长期优化
- LLM-based intent classification替代keyword matching
- Cross-encoder reranker (BGE-reranker)
- A/B testing framework
