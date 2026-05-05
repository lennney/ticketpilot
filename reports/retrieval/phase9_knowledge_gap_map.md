# Phase 9.3 — Knowledge Gap Mapping: From Taxonomy to Actionable Knowledge Needs

*Generated at 2026-05-05 UTC*
*Part of Phase 9: Evaluation-driven Knowledge Coverage Optimization*
*OpenSpec Change: add-evaluation-driven-knowledge-coverage*

> **Boundary statements:**
> - This is a local demo / portfolio prototype using synthetic data.
> - All 101 eval tickets and 95 knowledge records are synthetic / adapted / public-source-inspired.
> - This is offline evaluation, not online A/B testing.
> - No real enterprise customer data is used anywhere.
> - The system is draft-only and human-in-the-loop.
> - Phase 9 does not claim production benchmark results.
> - This document is analysis/report-only: no runtime code, data, or baseline report modifications.

---

## 1. Baseline from Phase 9.2 Taxonomy

### Taxonomy Distribution

| Category | Count | % of 41 | Requires Knowledge Expansion? |
|----------|-------|---------|------------------------------|
| `missing_case` | 11 | 26.8% | ✅ Yes — Case records |
| `missing_policy` | 9 | 22.0% | ✅ Yes — Policy records |
| `business_domain_gap` | 6 | 14.6% | ✅ Yes — Cross-type (FAQ+Policy+Case) |
| `golden_label_gap` | 4 | 9.8% | ❌ No — Label fix |
| `risk_level_gap` | 3 | 7.3% | ✅ Yes — Risk-tagged records |
| `missing_faq` | 1 | 2.4% | ✅ Yes — FAQ records |
| `query_expansion_gap` | 4 | 9.8% | ❌ No — Query builder fix |
| `doc_type_mismatch` | 2 | 4.9% | ❌ No — Retrieval balance tuning |
| `needs_manual_review` | 1 | 2.4% | ❌ No — Manual trace review |

### Key Distinction

| Bucket | Count | % |
|--------|-------|---|
| **Knowledge gaps** (Case + Policy + FAQ + cross-type + risk) | **30** | **73.2%** |
| **Non-knowledge gaps** (labels + query + mismatch + review) | **11** | **26.8%** |

**Not all 41 wrong cases should be fixed by adding knowledge.** 11 cases require label fixes, query builder changes, or manual investigation.

---

## 2. Knowledge Gap Mapping Table

### 2.1 FAQ Gaps

| Gap ID | Source Taxonomy | Related Case IDs | Business Domain | Proposed Knowledge Need | Priority | Phase 9.4 Action |
|--------|---------------|-----------------|----------------|------------------------|----------|-----------------|
| KG-FAQ-001 | preventive¹ | comp_010 | complaint | FAQ about投诉入口位置和如何使用投诉功能 | P1 | Add 1 FAQ |
| KG-FAQ-002 | preventive¹ | comp_011 | complaint | FAQ about界面字体大小调节/无障碍模式设置 | P2 | Add 1 FAQ |
| KG-FAQ-003 | missing_faq | retu_004 | return_exchange | FAQ about换货商品缺货时的可选方案 | P2 | Add 1 FAQ |

¹Not among the 41 wrong cases. Preventive addition identified during analysis.

### 2.2 Policy Gaps

| Gap ID | Source Taxonomy | Related Case IDs | Business Domain | Proposed Knowledge Need | Priority | Phase 9.4 Action |
|--------|---------------|-----------------|----------------|------------------------|----------|-----------------|
| KG-POL-001 | missing_policy | refu_001, refu_006 | refund | Policy about退款超时未到账时的投诉升级路径和处理时限 | P0 | Add 1 Policy |
| KG-POL-002 | missing_policy | refu_013 | refund | Policy about疑似假货/仿冒品的鉴定流程、赔偿标准和报案配合义务 | P0 | Add 1 Policy |
| KG-POL-003 | missing_policy | acco_003, acco_006, acco_012 | account | Policy about个人信息泄露/实名冒用/身份盗用的处理流程和平台责任边界 | P0 | Add 1-2 Policies |
| KG-POL-004 | missing_policy | othe_011, othe_012, othe_013 | other | Policy about发票争议处理：逾期未开、金额不符、个人被拒开票 | P1 | Add 1 Policy |
| KG-POL-005 | missing_policy | refu_009 (partial) | refund | Policy about用户发出法律威胁时的退款处理边界和法务对接规则 | P0 | Add 1 Policy |

### 2.3 Case Gaps

| Gap ID | Source Taxonomy | Related Case IDs | Business Domain | Proposed Knowledge Need | Priority | Phase 9.4 Action |
|--------|---------------|-----------------|----------------|------------------------|----------|-----------------|
| KG-CASE-001 | missing_case | comp_001 | complaint | Case about用户投诉客服态度的处理过程和结果（道歉+培训+补偿） | P0 | Add 1 Case |
| KG-CASE-002 | missing_case | comp_002, refu_013 | complaint / refund | Case about用户因怀疑假货要求赔偿的处理过程（鉴定+退款+赔付） | P0 | Add 1 Case |
| KG-CASE-003 | missing_case | comp_003 | complaint | Case about促销折扣未兑现的投诉处理和补偿方案 | P0 | Add 1 Case |
| KG-CASE-004 | missing_case | comp_006 | complaint | Case about用户投诉至12315等外部平台的升级处理流程 | P0 | Add 1 Case |
| KG-CASE-005 | missing_case | comp_007 | complaint | Case about商品与描述不符的投诉处理和补偿标准 | P0 | Add 1 Case |
| KG-CASE-006 | missing_case | comp_008 | complaint | Case about售后渠道（电话+在线）均无法接通时的升级处理 | P0 | Add 1 Case |
| KG-CASE-007 | missing_case | logi_008 | logistics | Case about物流信息长时间不更新的催单升级和补发处理 | P1 | Add 1 Case |
| KG-CASE-008 | missing_case | retu_006 | return_exchange | Case about换货后商品仍有质量问题的二次处理（再次换货或退款） | P1 | Add 1 Case |
| KG-CASE-009 | missing_case | retu_010 | return_exchange | Case about7天退货被拒后的用户投诉升级处理 | P1 | Add 1 Case |
| KG-CASE-010 | missing_case | retu_011 | return_exchange | Case about换货处理超过15天的催办升级和安抚方案 | P1 | Add 1 Case |

### 2.4 Cross-type Gaps (Business Domain)

| Gap ID | Source Taxonomy | Related Case IDs | Business Domain | Proposed Knowledge Need | Priority | Phase 9.4 Action |
|--------|---------------|-----------------|----------------|------------------------|----------|-----------------|
| KG-MIX-001 | business_domain_gap | refu_009, refu_015 | refund / complaint | Cross-type coverage for legal-threat+refund-delay scenarios: FAQ(法律威胁应对)+Policy(长期退款+赔偿规则)+Case(法律威胁+退款案例) | P0 | Add 1 FAQ + 1 Policy + 1 Case |
| KG-MIX-002 | business_domain_gap | acco_009, acco_014 | account | Cross-type coverage for account-ban-ID-theft scenarios: Policy(永久封禁申诉)+Case(身份证冒用开户) | P0 | Add 1 Policy + 1 Case |
| KG-MIX-003 | business_domain_gap | comp_005, comp_013 | complaint / account | Cross-type coverage for data-leak-threat scenarios: Policy(隐私泄露法律责任)+Case(数据泄露导致骚扰/威胁) | P0 | Add 1 Policy + 1 Case |

### 2.5 Risk-level Gaps

| Gap ID | Source Taxonomy | Related Case IDs | Business Domain | Proposed Knowledge Need | Priority | Phase 9.4 Action |
|--------|---------------|-----------------|----------------|------------------------|----------|-----------------|
| KG-RISK-001 | risk_level_gap | comp_004, comp_009 | complaint | HIGH-risk Case about法律威胁+书面道歉要求+大额赔偿的处理过程和审批链 | P0 | Add 1-2 HIGH-risk Cases |
| KG-RISK-002 | risk_level_gap | refu_003 | refund | MEDIUM-risk Policy+Case about超出售后期限退款+用户投诉的综合处理 | P1 | Update risk annotation on existing Policy; add Case |
| KG-RISK-003 | risk_level_gap | acco_003 | account | HIGH-risk Case about手机号泄露导致骚扰+用户投诉的平台处理（已在Policy gap KG-POL-003中覆盖Case部分） | P0 | Add HIGH-risk Case matching KG-POL-003 |

---

## 3. Recommended Knowledge Expansion Plan

### Summary Table

| Expansion Type | Count | Priority Cases | Rationale |
|---------------|-------|----------------|-----------|
| New Case records | 10-13 | comp_001-008, refu_013, logi_008, retu_006/010/011 | Largest gap category (26.8%). Complaint scenarios are the highest-traffic intent with 77% wrong rate. |
| New Policy records | 5-7 | refu_001/006, refu_013, acco_003/006/012, othe_011/012/013 | Second largest (19.5%). Privacy, refund-escalation, and invoice rules are missing. |
| Cross-type records | 3-5 | refu_009/015, acco_009/014, comp_005/013 | Business domain gaps (14.6%) need coordinated FAQ+Policy+Case expansion. |
| Risk-tagged records | 2-3 | comp_004/009, refu_003 | Risk_level_gap (7.3%) requires HIGH/MEDIUM-risk annotated Case records. |
| New FAQ records | 1-3 | retu_004; optional preventive (comp_010/011) | Smallest gap (2.4%). One addresses a wrong case; others are preventive. |
| **Total new records** | **21-31** | — | Expands from 95 → **116-126** knowledge records. |

### Priority Order

1. **P0 — Case for complaint scenarios** (comp_001-008): 8 cases, most with HIGH/MEDIUM
2. **P0 — Policy for refund escalation** (refu_001, refu_006): addresses 2 common refund delays
3. **P0 — Cross-type for legal threats** (refu_009, refu_015): legal-risk + refund-delay combo
4. **P0 — Policy for privacy/security** (acco_003/006/012): data leak and identity fraud
5. **P0 — Risk-level Case+Policy** (comp_004/009): HIGH-risk complaint escalation
6. **P1 — Policy for invoice disputes** (othe_011/012/013): billing accuracy
7. **P1 — Case for logistics** (logi_008): delivery delay escalation
8. **P1 — Case for return/exchange** (retu_006/010/011): quality escalation
9. **P2 — FAQ for UI/accessibility** (comp_010/011, preventive): lower business impact; does not fix any wrong case

> **Important:** These are recommendations for Phase 9.4 synthetic knowledge expansion in a demo/portfolio context. They do not represent production knowledge base requirements or real enterprise coverage expectations. Actual production deployment would require domain-expert review and real business process documentation.

---

## 4. Non-knowledge Workstream (plus Manual Review)

### Non-knowledge (10 cases — labels, query, mismatch)

| Workstream | Count | Case IDs | Why Not Knowledge Expansion | Suggested Action |
|-----------|---|---------|---------------------------|-----------------|
| **golden_label_gap** | 4 | edge_001, edge_003, edge_004, edge_005 | Empty `expected_evidence_doc_types` means evaluation cannot determine correct retrieval. Adding knowledge won't fix undefined expectations. | Review and add reasonable expected_evidence_doc_types. Edge_001 retrieves docs but golden expects nothing — add based on retrieved content. For edge_003-005, mark as known empty or add types reflecting the intent. |
| **query_expansion_gap** | 4 | logi_005, logi_010, logi_011, othe_009 | Relevant knowledge exists in the knowledge base but retrieval query does not surface it. Adding more records would not help if the query can't match. | Inspect `build_retrieval_query()` output for logistics and duplicate-charge scenarios. Likely issues: query terms too generic, missing synonyms, or intent classification not matching knowledge domain. |
| **doc_type_mismatch** | 2 | refu_008, refu_016 | Knowledge exists but the wrong doc_type dominates top ranks (FAQ/Case above Policy). Adding more records would further dilute Policy presence. | Review RRF fusion weights or FTS scoring for Policy documents in return-related queries. Consider whether Policy should be boosted in this context. |
| | | | |
| **Manual review only (separate from non-knowledge)** | | | | |
| **needs_manual_review** | 1 | edge_002 | Empty retrieval for very long mixed-language text. Could be data pipeline, tokenization, or DB query issue — not a knowledge problem. | Manual trace review: check if text exceeds processing limits, verify DB query for special characters, inspect hybrid retrieval behavior. |

### Non-knowledge Priority

| Workstream | Effort | Potential Impact | Recommended Phase |
|-----------|--------|-----------------|------------------|
| golden_label_gap | Low (~30 min) | Could fix 4 wrong cases directly | Before Phase 9.4 |
| query_expansion_gap | Low-Medium (~1-2 hr) | Could fix 4 wrong cases indirectly | Parallel to Phase 9.4 |
| doc_type_mismatch | Medium (~2-4 hr) | Could fix 2 wrong cases, but risk of regression | After Phase 9.4 evaluation |
| | | | |
| **Manual review only** | | | |
| needs_manual_review | Low (~1 hr) | Diagnostic only; fix TBD | Before or during Phase 9.4 |

---

## 5. Phase 9.4 Input Checklist

Before adding any knowledge record in Phase 9.4, the following fields MUST be documented for traceability:

### Knowledge Record Checklist

| Field | Required | Example |
|-------|----------|---------|
| `target_doc_type` | ✅ | FAQ / Policy / Case |
| `business_domain` | ✅ | complaint / refund / account / logistics / return_exchange |
| `risk_level` | ✅ (if Case) | low / medium / high |
| `source_table` | ✅ | faq_seed.json / policy_seed.json / case_seed.json |
| `synthetic_source_note` | ✅ | "Synthetic — based on Chinese e-commerce customer service domain knowledge" |
| `related_wrong_case_ids` | ✅ | comp_001, comp_002 |
| `gap_id_reference` | ✅ | KG-CASE-001 |
| `expected_behavior` | ✅ | "This Case should be retrieved as evidence for XYZ scenario" |
| `doc_level_golden_label_needed` | Optional | If this record is meant to be specifically evaluated, add to golden CSV |

### Non-knowledge Record Checklist

| Workstream | Precondition | Action |
|-----------|-------------|--------|
| golden_label_gap | Review and update `data/eval/golden_expectations.csv` | Add expected_evidence_doc_types to edge_001/003/004/005 |
| query_expansion_gap | Review `build_retrieval_query()` output for 4 cases | Modify query builder if terms are underspecified |
| doc_type_mismatch | Analyze RRF scores for Policy vs FAQ in return queries | Adjust fusion weights or FTS scoring if needed |

### Manual Review Checklist

| Case | Precondition | Action |
|------|-------------|--------|
| edge_002 (needs_manual_review) | Manual trace of case_edge_002 pipeline | Determine root cause and fix |

---

## 6. Product Manager Interpretation

### Why Phase 9.3 Is NOT "Adding Data"

Phase 9.3 bridges the gap between "what's wrong" (Phase 9.2 taxonomy) and "what to build" (Phase 9.4 expansion). Without this mapping:

- **"Add more knowledge" is a guess.** The taxonomy showed that Case content is the largest gap (26.8%), not FAQ (2.4%). If we blindly added 30 new FAQ records, we would fix at most 1 wrong case while missing the 11 that need Case coverage.
- **Adding knowledge doesn't fix non-knowledge problems.** 10 non-knowledge + 1 manual-review-only = 11 of 41 wrong cases would not be fixed by any amount of knowledge expansion — they require label fixes, query tuning, or manual debugging. Adding records for these would be wasted effort and could introduce noise.
- **Priority matters.** Complaint escalation scenarios (P0) affect 77% of complaint tickets. Invoice FAQ (P2) affects a single "other" ticket. Adding complaint Cases first has the highest ROI.

### Why Case Is Highest Priority

- 11 of 41 wrong cases lack Case evidence (26.8%)
- complaint intent has 77% wrong rate — the highest of any production intent
- The current 25 Case records are tilted toward consumer-favorable resolutions (refund granted, exchange processed). Complaint scenarios involving formal escalation (legal threats, 12315, counterfeits, undisclosed seller issues) have no matching precedent
- Case records provide the resolution narrative that a copilot needs for drafting: "What happened, how was it resolved, what was the compensation"
- Without Case coverage, the copilot draft can only reference generic FAQ instructions or Policy rules — not realistic outcomes

### Why Policy Is Second Priority

- 9 of 41 wrong cases lack Policy coverage (22.0%)
- Privacy leaks, identity fraud, and invoice disputes are recurring scenarios that need documented rules
- Unlike Case (which provides precedent), Policy provides the **rule boundary** — what the platform will and won't do
- Missing Policy means the draft has no authoritative source for "our policy on this is X"

### Why FAQ Is Lower Priority

- Only 1 of 41 wrong cases (2.4%) needs FAQ expansion; 2 additional FAQ additions are preventive (not fixing any wrong case)
- FAQ coverage is already strong at 40 records across all domains
- The sole wrong-case FAQ gap (retu_004, exchange-out-of-stock) is a narrow scenario; the 2 preventive additions (comp_010/011, UI navigation) have low business impact per case

### Why Golden Label and Query Expansion Must Be Separate Workstreams

- **Golden labels are a measurement problem, not a knowledge problem.** If the golden expects nothing (empty `expected_evidence_doc_types`), the evaluation cannot measure success. Fixing the labels fixes 4 wrong cases for free.
- **Query expansion is a retrieval engineering problem, not a knowledge problem.** If the knowledge exists but the query can't find it, adding more knowledge won't help — the new knowledge would also be invisible. Fixing query construction for 4 cases could recover multiple wrong cases without any data changes.

### Why This Is More Credible Than Blind Bulk Addition

1. **Taxonomy-driven targeting** — every proposed knowledge record is traced to a specific wrong case and gap category
2. **Priority-based sequencing** — P0 before P1 before P2, not random addition
3. **Non-knowledge separation** — 11 cases explicitly excluded from knowledge expansion, avoiding wasted effort
4. **Synthetic source transparency** — all records remain synthetic/adapted, no enterprise data
5. **Traceability** — each proposed record links back to the gap ID and case IDs it addresses, enabling before/after measurement

For a customer service copilot portfolio demo, this sequencing tells a coherent story: *"We found the bottleneck, diagnosed it with evaluation, and are now systematically closing the most impactful gaps — not fishing for metrics improvements."*

---

## 7. Validation Boundary

This document is strictly analysis/report-only:

- ❌ No runtime code modified (`src/`, `tests/`)
- ❌ No data files modified (`data/`)
- ❌ No baseline reports modified (`reports/retrieval/wrong_cases.md`, `reports/retrieval/fake_vs_real_comparison.*`)
- ❌ No embeddings rebuilt
- ❌ No database changes
- ❌ No `pyproject.toml`, `uv.lock`, `.env`, `.env.local` changes
- ❌ No claims of production benchmark performance
- ❌ No real enterprise customer data referenced
- ✅ `reports/retrieval/phase9_knowledge_gap_map.md` — new analysis report (this file)
- ✅ `openspec/changes/add-evaluation-driven-knowledge-coverage/tasks.md` — task progress update
- ✅ `docs/changelog.md` — Phase 9.3 changelog entry

---

## Appendix: Gap ID Full Index

| Gap ID | Category | Case Count | Total Records Needed |
|--------|----------|-----------|-------------------|
| KG-FAQ-001 | preventive¹ | 1 | 1 FAQ |
| KG-FAQ-002 | preventive¹ | 1 | 1 FAQ |
| KG-FAQ-003 | missing_faq | 1 | 1 FAQ |
| KG-POL-001 | missing_policy | 2 | 1 Policy |
| KG-POL-002 | missing_policy | 1 | 1 Policy |
| KG-POL-003 | missing_policy | 3 | 1-2 Policies |
| KG-POL-004 | missing_policy | 3 | 1 Policy |
| KG-POL-005 | missing_policy | 1 | 1 Policy |
| KG-CASE-001 | missing_case | 1 | 1 Case |
| KG-CASE-002 | missing_case | 2 | 1 Case |
| KG-CASE-003 | missing_case | 1 | 1 Case |
| KG-CASE-004 | missing_case | 1 | 1 Case |
| KG-CASE-005 | missing_case | 1 | 1 Case |
| KG-CASE-006 | missing_case | 1 | 1 Case |
| KG-CASE-007 | missing_case | 1 | 1 Case |
| KG-CASE-008 | missing_case | 1 | 1 Case |
| KG-CASE-009 | missing_case | 1 | 1 Case |
| KG-CASE-010 | missing_case | 1 | 1 Case |
| KG-MIX-001 | business_domain_gap | 2 | 1 FAQ + 1 Policy + 1 Case |
| KG-MIX-002 | business_domain_gap | 2 | 1 Policy + 1 Case |
| KG-MIX-003 | business_domain_gap | 2 | 1 Policy + 1 Case |
| KG-RISK-001 | risk_level_gap | 2 | 1-2 HIGH-risk Cases |
| KG-RISK-002 | risk_level_gap | 1 | 1 MEDIUM-risk Case + Policy update |
| KG-RISK-003 | risk_level_gap | 1 | (Covered by KG-POL-003 + KG-CASE case) |

### Count Summary by Phase 9.4 Action

| Action | Count |
|--------|-------|
| New Case records | 10-13 |
| New Policy records | 5-7 |
| New FAQ records | 1-3 |
| Total new knowledge records | 16-23 |
| Expanded knowledge base total | 95 → **111-118** |
