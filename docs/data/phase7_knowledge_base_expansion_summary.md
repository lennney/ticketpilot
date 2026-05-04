# Phase 7B-4: Knowledge Base Expansion Summary

## Expansion Counts

| Metric | Before | After |
|--------|-------:|------:|
| FAQ | 12 | 40 |
| Policy | 12 | 30 |
| Case | 12 | 25 |
| Total source records | 36 | 95 |
| knowledge_chunks | 36 | 95 |
| Chunks with source refs | 36 | 95 |
| Chunks with embeddings | 36 | 95 |

## Coverage by Topic

| Topic | FAQ | Policy | Case | Eval Scenarios Supported |
|-------|:---:|:------:|:----:|--------------------------|
| refund | 12 | 10 | 6 | refund, refund_complaint |
| return_exchange | 5 | 4 | 3 | return_exchange |
| account | 7 | 5 | 3 | account_issue |
| technical | 3 | 1 | 2 | technical_issue |
| product_consulting | 3 | 1 | 1 | product_consulting |
| logistics | 4 | 3 | 2 | logistics |
| complaint | 4 | 5 | 4 | complaint |
| invoice/payment | 2 | 1 | 1 | invoice, payment, billing |
| privacy/security | *(covered in account)* | *(covered in account)* | 2 | privacy, account_security |
| other | 2 | 1 | — | general inquiries |

## Risk Coverage

| Risk Flag | Related Knowledge |
|-----------|-------------------|
| complaint_risk | Complaint FAQ, complaint escalation policy, complaint cases |
| compensation_risk | Compensation handling policy, legal threat policy, compensation cases |
| legal_risk | Legal threat FAQ, lawyer letter policy, legal escalation cases |
| privacy_risk | Privacy policy, privacy leak escalation rule, privacy leak cases |
| account_security_risk | Account security FAQ, account security policy, stolen account cases |
| policy_conflict | Return policy policies, 7-day return limitation, exception handling policy |
| insufficient_evidence | Insufficient evidence policy, no-evidence case |
| low_confidence | *(addressed via evidence coverage breadth — the pipeline flags low confidence when insufficient evidence matches)* |

## Data Origin

All knowledge records are **synthetic / manually adapted** content:

- **FAQ**: Adapted from common e-commerce customer service scenarios. Written based on typical consumer questions observed in public forums and customer service handbooks. Not sourced from any real enterprise system.
- **Policy**: Policy-inspired records written to reflect common e-commerce platform policies (return windows, refund processing, complaint handling). Modeled after publicly available policy patterns, not copied from any specific platform's terms of service.
- **Case**: Synthetic case records representing typical resolution patterns. All case data is虚构 (fictional), no real customer data is included.

### Important Limitations

1. **No real enterprise data** — All knowledge is synthetic. It does not represent any real business's customer service data, policy documents, or case resolutions.
2. **Not representative of real business distribution** — Topic coverage is biased toward scenarios needed for evaluation (101 eval tickets), not toward actual business volume.
3. **Fake embeddings only** — The FakeEmbeddingProvider generates deterministic 384-dimensional vectors. This validates pipeline mechanics (seeding, chunking, retrieval flow) but does **not** provide semantic search quality. Real embedding provider integration is reserved for Phase 8.
4. **No deterministic payment promises** — Knowledge records do not guarantee specific payment amounts or timelines beyond what is stated.
5. **No auto-send** — No knowledge record states or implies automatic refund or automatic dispatch behavior.

## Representative doc_id List

| doc_id | Type | Title / Topic | Supports Eval Scenarios |
|--------|------|--------------|------------------------|
| `ffffffff-4444-4444-4444-444444444444` | FAQ | 收到律师函或法律威胁怎么办？ | complaint, legal_risk |
| `ae0e0e0e-9999-9999-9999-999999999999` | POLICY | 商品价格保护规则 | refund, price_adjustment |
| `ad0d0d0d-9999-9999-9999-999999999999` | POLICY | 法律威胁与律师函处理规则 | complaint, legal_risk |
| `ad0d0d0d-6666-6666-6666-666666666666` | POLICY | 隐私泄露升级处理规则 | privacy, account_security |
| `c1111111-1111-1111-1111-111111111111` | CASE | 律师函赔偿案 | complaint, legal_risk, compensation |
| `c4444444-4444-4444-4444-444444444444` | CASE | 个人信息泄露案 | privacy, account_security |
| `c6666666-6666-6666-6666-666666666666` | CASE | 重复付款退款案 | refund, payment |
| `ad0d0d0d-3333-3333-3333-333333333333` | POLICY | 发票开具规则 | invoice |
| `ad0d0d0d-8888-8888-8888-888888888888` | POLICY | 投诉升级规则 | complaint |
| `ca0a0a0a-1111-1111-1111-111111111111` | CASE | 证据不足案 | no-evidence, insufficient_evidence |
| `ae0e0e0e-3333-3333-3333-333333333333` | POLICY | 证据不足处理规则 | no-evidence |
| `ad0d0d0d-1111-1111-1111-111111111111` | POLICY | 已拆封商品退换限制规则 | return_exchange, policy_conflict |
| `c9999999-9999-9999-9999-999999999999` | CASE | 超出售后期限退货案 | return_exchange, policy_conflict |
| `ae0e0e0e-2222-2222-2222-222222222222` | POLICY | 超出售后期限例外处理规则 | refund, policy_conflict |
| `ae0e0e0e-1111-1111-1111-111111111111` | POLICY | 赔偿诉求处理规则 | complaint, compensation |
| `c5555555-5555-5555-5555-555555555555` | CASE | 账号异地登录案 | account_security |

## Files Changed

| File | Action |
|------|--------|
| `data/knowledge/faq_seed.json` | Expanded 12 → 40 records |
| `data/knowledge/policy_seed.json` | Expanded 12 → 30 records |
| `data/knowledge/case_seed.json` | Expanded 12 → 25 records |
| `docs/data/phase7_knowledge_base_expansion_summary.md` | Created (this file) |
