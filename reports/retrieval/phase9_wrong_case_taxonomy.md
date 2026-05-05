# Phase 9.2 — Wrong-case Taxonomy: Refined Classification of Phase 8 Retrieval Failures

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

---

## 1. Phase 8 Baseline Recap

| Metric | Fake 384-d | Real 1024-d | Delta |
|--------|-----------|------------|-------|
| Eval cases | 101 | 101 | — |
| Top-1 hit rate | 31.7% | 42.6% | +10.9% |
| Top-3 hit rate | 47.5% | 56.4% | +8.9% |
| Top-5 hit rate | 53.5% | 58.4% | +5.0% |
| Top-10 hit rate | 59.4% | 59.4% | 0.0% |
| MRR | 0.4114 | 0.4913 | +0.0799 |
| **Wrong cases (Top-10)** | **41** | **41** | **0** |

**Key finding:** Real embedding improves ranking (Top-1 +10.9%, MRR +0.0799) but does not reduce wrong-case count. All 41 wrong cases are classified as `missing_doc_type` — at least one expected document type absent from Top-10 results. The bottleneck is **knowledge coverage**, not embedding quality.

### Intent Distribution of Wrong Cases

| Intent | Wrong Cases | Total Cases | % Wrong |
|--------|-------------|-------------|---------|
| complaint | 10 | 13 | 77% |
| refund | 8 | 16 | 50% |
| return_exchange | 5 | 11 | 45% |
| account_issue | 5 | 15 | 33% |
| logistics | 4 | 11 | 36% |
| other | 4 | 13 | 31% |
| edge | 5 | 5 | 100% |

### Empty Retrieval Cases

4 cases return zero retrieved documents:

| Case ID | Expected | Notes |
|---------|----------|-------|
| case_edge_002 | [Case, Policy] | Empty retrieval — knowledge missing |
| case_edge_003 | [] | Empty expected + empty retrieval |
| case_edge_004 | [] | Empty expected + empty retrieval |
| case_edge_005 | [] | Empty expected + empty retrieval |

---

## 2. Taxonomy Definition

### Refined Categories

| # | Category | Definition | Likely Next Action |
|---|----------|------------|-------------------|
| 1 | `missing_faq` | No FAQ record covers the intent/domain combination needed for this ticket. Expected FAQ doc_type is absent from Top-10. | Add FAQ seed record |
| 2 | `missing_policy` | No Policy record covers the rule/compliance/compensation topic. Expected Policy doc_type is absent from Top-10. | Add Policy seed record |
| 3 | `missing_case` | No Case record covers the scenario/precedent. Expected Case doc_type is absent from Top-10. | Add Case seed record |
| 4 | `doc_type_mismatch` | Retrieved docs exist but the doc_type found does not match the expected type (e.g., FAQ is retrieved but Policy is expected). | Review query construction or retrieval balance |
| 5 | `business_domain_gap` | The entire business domain (e.g., legal threats, counterfeit goods, false promotion) has sparse or no cross-type coverage. | Add domain-specific records across types |
| 6 | `risk_level_gap` | Knowledge lacks records annotated at the ticket's required risk level (e.g., HIGH-risk ticket needs HIGH-risk Case evidence). | Add risk-tagged records at appropriate levels |
| 7 | `query_expansion_gap` | Relevant knowledge exists in the knowledge base but the retrieval query does not match it (underspecified terms, wrong field). | Improve query builder logic |
| 8 | `golden_label_gap` | Golden expectations are incomplete: empty `expected_evidence_doc_types` or the expected types do not reflect actual ticket needs. | Fix golden labels in CSV |

### Boundary Cases

| Category | Note |
|----------|------|
| `needs_manual_review` | Cases where multiple factors overlap and cannot be reliably decomposed without per-query trace analysis |

---

## 3. Wrong-case Distribution (Refined Taxonomy)

### Summary Table

| Taxonomy | Count | % of 41 | Primary Intent Cluster |
|----------|-------|---------|----------------------|
| `missing_case` | 11 | 26.8% | complaint (6), refund (1), logistics (1), return (3) |
| `missing_policy` | 9 | 22.0% | account (3), refund (2), other (3), return (1) |
| `missing_faq` | 1 | 2.4% | return (1) |
| `business_domain_gap` | 6 | 14.6% | refund (3), account (2), complaint (1) |
| `risk_level_gap` | 3 | 7.3% | complaint (2), refund (1) |
| `golden_label_gap` | 4 | 9.8% | edge (4) |
| `query_expansion_gap` | 4 | 9.8% | logistics (3), other (1) |
| `doc_type_mismatch` | 2 | 4.9% | refund (1), return (1) |
| `needs_manual_review` | 1 | 2.4% | edge (1) |
| **Total** | **41** | **100%** | — |

### Analysis: Why These Categories?

#### `missing_case` (11 cases) — Largest Single Category

**Pattern:** Tickets expected Case evidence but no relevant Case document was retrieved. The knowledge base has 25 Case records, but coverage is biased toward consumer-favorable scenarios (refund granted, exchange processed). Many complaint scenarios lack matching Case precedents:

| Cases | Scenario | Gap |
|-------|----------|-----|
| comp_002, comp_004, comp_009 | 假货/书面道歉/卖家失联 | No Case for counterfeit goods, formal apology, or seller-disappearance scenarios |
| comp_006, comp_008, comp_013 | 消协投诉/售后渠道/地址泄露 | Consumer-association complaints, inaccessible after-sales, address data leaks have thin Case coverage |
| refu_008, refu_009 | 退货运费/法律威胁 | Policy mentions wrong-item return shipping but no Case illustrates the resolution; legal-threat Case exists (c1111111) but may not match query |
| logi_008 | 物流三天未更新 | No Case for "at local hub for 3 days" — only general lost-package Cases exist |
| retu_011 | 换货处理逾半个月 | No Case for "exchange stuck in processing for 2+ weeks" |

**Next action:** Add ~8-10 targeted Case records covering complaint escalation, legal threats, counterfeit goods, invoice disputes, and logistics delay precedents.

#### `missing_policy` (9 cases) — Second Largest

**Pattern:** Tickets expected Policy evidence but the relevant policy was not retrieved. Current 30 policies cover the basics but miss nuanced scenarios:

| Cases | Scenario | Gap |
|-------|----------|-----|
| refu_001, refu_006 | 退款逾期/12315投诉 | Policies cover refund timing (ad0d0d0d-2222) and complaint escalation (ad0d0d0d-8888) but cross-cutting "refund delay + external complaint" is not explicitly covered |
| refu_013, refu_015 | 假货赔偿+报案/退款一月未到 | No policy for counterfeit-goods compensation procedure or 30+ day refund escalation |
| acco_003, acco_012 | 手机号泄露/身份信息被盗用 | Privacy policies exist (ad0d0d0d-6666) but may not match the query for privacy + multi-account scenarios |
| retu_004 | 换货无货要求补偿 | No policy for "exchange out of stock → compensation" scenario |
| othe_012 | 发票金额300实付500 | Invoice policy exists (ad0d0d0d-3333) but doesn't cover amount discrepancy procedure |

**Next action:** Add ~5-7 targeted Policy records covering counterfeit procedure, refund-escalation-length scenarios, invoice-discrepancy handling, and exchange-out-of-stock compensation rules.

#### `missing_faq` (1 case)

| Cases | Scenario | Gap |
|-------|----------|-----|
| retu_004 | 换货无货要求补偿 | FAQ has return policy but not "exchange out of stock" scenario |

> **Note:** `comp_010` (找不到投诉入口) and `comp_011` (字体太小) were identified as FAQ gaps during analysis but are NOT among the 41 wrong cases. They could be added as preventive coverage in Phase 9.4 but would not fix existing wrong cases.

**Next action:** Add 1 FAQ for exchange-out-of-stock scenario.

#### `business_domain_gap` (6 cases)

**Pattern:** The business domain itself (e.g., privacy/security with legal implications, counterfeit goods, formal legal threats) has thin cross-type coverage. Even across FAQ + Policy + Case, the domain is not well represented:

| Cases | Domain | Gap |
|-------|--------|-----|
| refu_009, refu_015 | 法律威胁/长期退款 | Legal-threat + refund-delay combo has no dedicated FAQ, Policy, or Case coverage |
| acco_006, acco_014 | 实名被冒用/身份证被盗 | ID theft and real-name fraud has FAQ (account security) but no dedicated Policy or Case |
| comp_005, comp_013 | 隐私泄露/被骚扰/地址泄露 | Data leak + spam calls scenario crosses privacy, security, and complaint domains with thin coverage |

**Next action:** This requires cross-type expansion rather than single-type fixes. Add 1-2 FAQ + 1-2 Policy + 1-2 Case for each hot domain.

#### `risk_level_gap` (3 cases)

**Pattern:** The ticket has HIGH or MEDIUM risk flags (legal_risk, compensation_risk, complaint_risk) and the retrieved evidence lacks risk-appropriate Case/Policy records:

| Cases | Risk Flags | Gap |
|-------|-----------|-----|
| comp_002, comp_004 | complaint_risk;legal_risk HIGH | HIGH-risk legal complaints need HIGH-risk Case evidence |
| refu_003 | policy_conflict;complaint_risk MEDIUM | Medium-risk with policy conflict needs matched Policy+Case |
| acco_003 | privacy_risk;complaint_risk HIGH | HIGH-risk privacy incident needs Case + Policy at matched risk level |

**Next action:** Audit risk_level annotations on existing Case records. Add risk-level metadata to Policy records where missing. Create high-risk Case records for legal/complaint escalation scenarios.

#### `golden_label_gap` (4 cases)

**Pattern:** Golden expectations have empty `expected_evidence_doc_types`:

| Case ID | Issue |
|---------|-------|
| case_edge_001 | Expected [] — golden label is empty, but retrieved docs exist. Cannot determine what "success" looks like |
| case_edge_003 | Expected [] — golden label empty, no retrieval |
| case_edge_004 | Expected [] — golden label empty, no retrieval |
| case_edge_005 | Expected [] — golden label empty, no retrieval |

**Next action:** Review and add reasonable `expected_evidence_doc_types` for edge cases. Edge_001 could be marked as "FAQ" since documents IS retrieved.

#### `query_expansion_gap` (4 cases)

**Pattern:** The knowledge base has relevant records, but the retrieval query does not surface them:

| Cases | Scenario |
|-------|----------|
| logi_005, logi_011 | 拒收破损包裹/时效赔偿 — logistics Cases exist (b8888888, c8888888) and Policies exist (a8888888, ae0e0e0e-6666) but were not surfaced in Top-10 |
| othe_009 | 重复扣款 — duplicate charge FAQ (dddddddd-9999) and Policy (ad0d0d0d-4444) exist, but were not among top results |

**Next action:** Review `build_retrieval_query()` output for these cases. The query terms may not encode "damaged+refused" or "duplicate+charge" correctly.

#### `doc_type_mismatch` (2 cases)

**Pattern:** Retrieved docs exist but the expected doc_type is nearly buried or absent from the retrieved set. In both cases, FAQ and Case documents dominate top ranks, and the relevant Policy type is either at the bottom of Top-10 or absent:

| Cases | Expected | Retrieved Pattern |
|-------|----------|-------------------|
| refu_008 | [Policy] | FAQ+CASE dominate ranks 1-8; Policy appears at rank 9-10 |
| refu_016 | [Case, Policy] | Price-difference Policy not surfaced; FAQ dominates |

#### `needs_manual_review` (1 case)

| Case ID | Reason |
|---------|--------|
| case_edge_002 | Expected [Case, Policy] but returns empty retrieval. Unusual pattern that may be a data ingestion issue. The ticket text is very long with mixed Chinese/English — possibly hitting token or encoding issues |

---

## 4. Case-level Mapping

Below is the full per-case mapping of all 41 wrong cases with refined taxonomy and next actions.

| Case ID | Intent | Expected Types | Refined Taxonomy | Suggested Next Action |
|---------|--------|---------------|-------------------|----------------------|
| case_acco_003 | account_issue | [Case, Policy] | `missing_policy` | Add privacy-leak-specific Policy |
| case_acco_006 | account_issue | [Case, Policy] | `missing_policy` | Add real-name-fraud Policy |
| case_acco_009 | account_issue | [Case, Policy] | `business_domain_gap` | Account ban appeal has no cross-type coverage |
| case_acco_012 | account_issue | [Case, Policy] | `missing_policy` | Add multi-account ID fraud Policy |
| case_acco_014 | account_issue | [Case, Policy] | `business_domain_gap` | ID-theft account opening needs FAQ+Policy+Case |
| case_comp_001 | complaint | [Case] | `missing_case` | Add customer-service-attitude complaint Case |
| case_comp_002 | complaint | [Case, Policy] | `missing_case` | Add counterfeit-goods accusation Case |
| case_comp_003 | complaint | [Case, Policy] | `missing_case` | Add promotion-discount-not-honored Case |
| case_comp_004 | complaint | [Case, Policy] | `risk_level_gap` | HIGH-risk written apology+compensation needs matched Case |
| case_comp_005 | complaint | [Case, Policy] | `business_domain_gap` | Data leak + spam calls needs privacy+complaint cross-coverage |
| case_comp_006 | complaint | [Case] | `missing_case` | Add consumer-association complaint escalation Case |
| case_comp_007 | complaint | [Case, Policy] | `missing_case` | Add product-not-as-described complaint Case |
| case_comp_008 | complaint | [Case] | `missing_case` | Add after-sales-channel-unreachable Case |
| case_comp_009 | complaint | [Case, Policy] | `risk_level_gap` | HIGH-risk seller-disappearance needs Case+Policy |
| case_comp_013 | complaint | [Case, Policy] | `business_domain_gap` | Address leak + threats needs privacy+complaint cross-coverage |
| case_edge_001 | edge | [] | `golden_label_gap` | Add expected doc types to golden |
| case_edge_002 | edge | [Case, Policy] | `needs_manual_review` | Check data pipeline for very long text |
| case_edge_003 | edge | [] | `golden_label_gap` | Add expected doc types to golden |
| case_edge_004 | edge | [] | `golden_label_gap` | Add expected doc types to golden |
| case_edge_005 | edge | [] | `golden_label_gap` | Add expected doc types to golden |
| case_logi_005 | logistics | [Case, Policy] | `query_expansion_gap` | Knowledge exists but query may miss "refused+damaged" terms |
| case_logi_008 | logistics | [Case] | `missing_case` | Add logistics-delay-escalation Case |
| case_logi_010 | logistics | [Case, Policy] | `query_expansion_gap` | Delivered-to-wrong-address has Case (b9999999) but not surfaced |
| case_logi_011 | logistics | [Case, Policy] | `query_expansion_gap` | Failed next-day-delivery has Policy (a7777777) but not surfaced |
| case_othe_009 | other | [Case, Policy] | `query_expansion_gap` | Duplicate charge FAQ+Policy exist but not retrieved |
| case_othe_011 | other | [Case, Policy] | `missing_policy` | Invoice-pending-1-month needs escalation Policy |
| case_othe_012 | other | [Case, Policy] | `missing_policy` | Invoice amount discrepancy needs Policy |
| case_othe_013 | other | [Case, Policy] | `missing_policy` | Invoice-denied-to-individual needs Policy |
| case_refu_001 | refund | [Case, Policy] | `missing_policy` | Refund-not-received + complaint needs refund-escalation Policy |
| case_refu_003 | refund | [Case, Policy] | `risk_level_gap` | Past-window refund+complaint needs matched-risk Policy |
| case_refu_006 | refund | [Case, Policy] | `missing_policy` | 10-day-delay+12315 threat needs escalation Policy |
| case_refu_008 | refund | [Case, Policy] | `doc_type_mismatch` | Wrong-item-return-shipping Policy is buried under FAQ/Case |
| case_refu_009 | refund | [Case, Policy] | `business_domain_gap` | Legal-threat+refund needs cross-type coverage |
| case_refu_013 | refund | [Case, Policy] | `missing_case` | Counterfeit-bag+compensation needs Case |
| case_refu_015 | refund | [Case, Policy] | `business_domain_gap` | 30-day refund delay + compensation needs cross-type coverage |
| case_refu_016 | refund | [Case, Policy] | `doc_type_mismatch` | Price-difference-refund Policy not surfaced under FAQ |
| case_retu_004 | return_exchange | [Case, Policy] | `missing_faq` | Exchange-out-of-stock FAQ missing |
| case_retu_006 | return_exchange | [Case, Policy] | `missing_case` | Replacement-also-defective Case missing |
| case_retu_008 | return_exchange | [Policy] | `missing_policy` | Return-shipping-dispute Policy not surfaced |
| case_retu_010 | return_exchange | [Case, Policy] | `missing_case` | 7-day-return-rejected escalation Case missing |
| case_retu_011 | return_exchange | [Case] | `missing_case` | Exchange-stuck-2-weeks Case missing |

---

## 5. FAQ / Policy / Case Gap Summary

### Which Cases Need FAQ Expansion (3 cases + 1 cross-type)

- `case_retu_004` — exchange out of stock: what happens? Add FAQ.
- `case_comp_010` — can't find complaint入口: UI navigation FAQ.
- `case_comp_011` — font too small: accessibility FAQ.
- Also consider FAQ for `case_othe_009` (duplicate charge) — FAQ exists (dddddddd-9999) but not surfaced — this is query_expansion_gap, not missing FAQ.

**Priority: LOW.** FAQ coverage is already strong (40 records). Missing FAQ affects only 7.3% of wrong cases.

### Which Cases Need Policy Expansion (8 cases + 1 cross-type)

- `case_refu_001, case_refu_006` — refund delay + escalation procedure
- `case_refu_013` — counterfeit goods compensation process
- `case_acco_003, case_acco_006, case_acco_012` — privacy leaks, real-name fraud, multi-account ID fraud
- `case_othe_011, case_othe_012, case_othe_013` — invoice disputes (pending, amount discrepancy, denial)

**Priority: HIGH.** Missing Policy affects 19.5% of wrong cases. The policy coverage gap is concentrated in privacy/invoice/complaint escalation domains.

### Which Cases Need Case Expansion (10 cases + 1 cross-type)

- `case_comp_001, case_comp_002, case_comp_003, case_comp_006, case_comp_007, case_comp_008` — various complaint scenarios without matching precedent
- `case_refu_013` — counterfeit compensation
- `case_logi_008` — logistics delay escalation
- `case_retu_006, case_retu_010, case_retu_011` — defective replacement, return rejection, stuck exchange

**Priority: HIGHEST.** Missing Case is the largest single category (24.4%). Complaint scenarios are disproportionately affected (6 of 10 missing_case are complaint intents).

### Which Cases Should NOT Be Fixed by Adding Knowledge

**Golden label fixes needed (4 cases):**
- `case_edge_001, case_edge_003, case_edge_004, case_edge_005` — add `expected_evidence_doc_types` to golden CSV

**Query expansion fixes needed (4 cases):**
- `case_logi_005, case_logi_010, case_logi_011, case_othe_009` — knowledge exists (logistics Cases/Policies, duplicate-charge FAQ+Policy) but query doesn't surface it

**Doc type mismatch (2 cases):**
- `case_refu_008, case_refu_016` — relevant Policy exists but FAQ/Case dominate top ranks. This is a retrieval balance issue, not missing knowledge.

**`needs_manual_review` (1 case):**
- `case_edge_002` — empty retrieval for very long mixed-language text. Could be a pipeline issue.

### Summary: What to Add vs What to Fix

| Action | Count | % of 41 |
|--------|-------|---------|
| Add Case records | 11 | 26.8% |
| Add Policy records | 9 | 22.0% |
| Add FAQ records | 1 | 2.4% |
| Add cross-type records (business_domain_gap) | 6 | 14.6% |
| Add risk-tagged records (risk_level_gap) | 3 | 7.3% |
| Fix golden labels | 4 | 9.8% |
| Fix query expansion | 4 | 9.8% |
| Fix retrieval balance (doc_type_mismatch) | 2 | 4.9% |
| Manual review | 1 | 2.4% |

---

## 6. Product Interpretation

### Why Phase 9.2 Is NOT an Embedding Optimization

Phase 8 already demonstrated that switching from FakeEmbeddingProvider (384-d) to DashScope text-embedding-v4 (1024-d) measurably improves ranking: Top-1 hit rate up 10.9%, MRR up 0.0799. But the 41 wrong cases remained unchanged because the bottleneck is **content availability, not content ranking**.

A better embedding model can rank existing knowledge more effectively. But if the knowledge base has no Case document about "after-sales channel unreachable" or no Policy document about "refund delay escalation procedure," no embedding model can produce one. The retrieval ceiling is what exists in the knowledge base.

### Why Not Simply Add Large Quantities of Knowledge

Blindly adding more FAQ/Policy/Case records risks:
1. **Overfitting to 101 eval cases** — adding records that improve offline metrics but don't generalize
2. **Category imbalance** — adding too many of one doc_type and overwhelming the retrieval balance
3. **False positives** — adding knowledge that changes correct cases into wrong ones (regression)
4. **Diminishing returns** — adding records for scenarios already covered by existing knowledge

The taxonomy analysis shows that knowledge gaps are concentrated: 11 of 41 wrong cases need Case expansion, 9 need Policy expansion, and only 1 is a pure FAQ gap. Blind bulk addition would waste effort.

### Why Taxonomy First

The Phase 9.2 taxonomy refines a single `missing_doc_type` bucket into 8 actionable categories:

1. **It prevents "shooting in the dark."** Without this breakdown, "add more knowledge" is a guess. With the breakdown, we know complaint-related Case records are the single highest-impact addition.
2. **It separates knowledge problems from non-knowledge problems.** 10 non-knowledge + 1 manual-review-only = 11 of 41 wrong cases would NOT be fixed by adding knowledge. Adding records for these would be wasted effort.
3. **It prioritizes by business impact.** complaint (77% wrong rate) and refund (50%) are the highest-traffic intent classes. The taxonomy shows these are also the most under-covered in Case evidence.
4. **It creates a baseline for Phase 9.3.** The gap mapping can start with concrete per-category counts rather than a generic "we need more docs."

### For a Customer Service Copilot Product

The product implication is clear: **coverage gaps are more dangerous than ranking gaps.**

In a copilot system that drafts replies for human agents:
- A correct but lower-ranked piece of evidence can still be reviewed by the agent (rank 3 vs rank 1)
- A missing piece of evidence means the draft will lack the right reference entirely
- The agent then either writes from scratch (wasting time) or approves an incomplete draft (risking quality)

By fixing knowledge coverage gaps before fine-tuning embedding models, the product path is:
1. Phase 8: Establish baseline metrics + prove ranking can improve
2. Phase 9: Fix knowledge coverage gaps — attack the primary bottleneck
3. Phase 10+: Return to embedding optimization once coverage is adequate

This sequencing prevents a common anti-pattern: optimizing ranking against an incomplete knowledge base, then changing the knowledge and needing to re-optimize.

---

## 7. Phase 9.3 Recommendations

### Priority Order for Knowledge Gap Mapping

1. **HIGHEST — Missing Case (complaint domain)**: Map all 6 complaint+Case gaps to specific Case scenarios. This is the single highest-impact fix.
2. **HIGH — Missing Policy (privacy/complaint)**: Map privacy-leak and invoice-dispute scenarios to Policy records.
3. **HIGH — Business domain gaps**: Map cross-type coverage for legal-threat, counterfeit-goods, and data-leak scenarios.
4. **MEDIUM — Risk level gaps**: Audit risk-level annotations on existing Case/Policy records.
5. **MEDIUM — Remaining missing Case/Policy**: Map refund-escalation and logistics-delay scenarios.
6. **LOW — Missing FAQ**: Map UI-navigation and accessibility FAQs.
7. **NON-KNOWLEDGE — Golden labels**: Fix 4 edge cases with empty expected doc types.
8. **NON-KNOWLEDGE — Query expansion**: Review `build_retrieval_query()` for logistic and duplicate-charge cases.
9. **MANUAL REVIEW — Edge case**: case_edge_002 empty retrieval.

### Recommended Knowledge Expansion Size

| Type | Count | Range |
|------|-------|-------|
| New Case records | 11 | Addresses `missing_case` + partial `business_domain_gap` |
| New Policy records | 8-9 | Addresses `missing_policy` + partial `risk_level_gap` |
| New FAQ records | 1-3 | Addresses `missing_faq`; optional preventive additions (comp_010, comp_011) |
| Cross-type records | 3-5 | Addresses `business_domain_gap` (legal threat, counterfeit, data leak) |
| **Total new records** | **23-28** | **Expands from 95 → ~118-123 knowledge records** |

### Should We Add Doc-Level Golden Labels?

**Yes, but optional.** Adding `expected_relevant_doc_ids` to golden expectations would:
- Enable Recall@K at document level (not just doc_type level)
- Distinguish "right doc_type, wrong specific doc" from "no doc of expected type at all"
- Improve wrong-case classification precision
- Currently, many cases in the wrong list appear to have the right doc_type but wrong content

**Recommendation:** Add doc-level golden labels for the 41 wrong cases as part of Phase 9.3, not for all 101 cases.

### Should We Check Query Expansion?

**Yes, for 3 specific cases.** `case_logi_005`, `case_logi_010`, `case_logi_011`, and `case_othe_009` have relevant knowledge in the base but it wasn't retrieved. This suggests the retrieval query doesn't encode the right terms. A query builder review for these 4 cases is low-effort and could fix 4 wrong cases without any knowledge expansion.

### Should We Retain `needs_manual_review` Cases?

**Keep `case_edge_002` unresolved** until a manual trace review confirms whether the empty retrieval is due to:
- Very long text exceeding a processing limit
- Encoding issues with mixed Chinese/English
- A legitimate zero-result query

---

## Taxonomy Cross-check: Category Overlap

Some cases could be assigned to multiple categories. This table shows which cases have secondary classifications:

| Case ID | Primary | Secondary | Reason |
|---------|---------|-----------|-------|
| case_refu_009 | `business_domain_gap` | `risk_level_gap` | Legal threat + HIGH risk, both policy and case missing |
| case_refu_015 | `business_domain_gap` | `risk_level_gap` | 30-day delay + compensation, both missing |
| case_comp_004 | `risk_level_gap` | `missing_case` | HIGH-risk legal complaint needs Case regardless |
| case_comp_009 | `risk_level_gap` | `missing_case` | Seller disappeared + HIGH risk |
| case_retu_008 | `missing_policy` | `doc_type_mismatch` | Policy exists but hard to retrieve |

Where a case has multiple valid categories, the primary category reflects the most actionable fix path.
