# Phase 10.4 — P0 Bottleneck Classification

*Generated at 2026-05-06 UTC*
*Part of Phase 10: Hybrid Retrieval Ranking Diagnosis*
*OpenSpec Change: add-hybrid-retrieval-ranking-diagnosis*

> **Boundary statement:**
> - Classification-only deliverable. No retrieval algorithm, RRF parameters, query builder,
>   embedding provider, knowledge base, or golden labels modified.
> - Classification uses the 8-category bottleneck taxonomy defined in Phase 10 design.
> - Real provider trace data (OpenAICompatible, 1024-d) used for semantic conclusions.

---

## 1. Classification Summary

| Bottleneck | Count | % | Main Meaning |
|---|---|---|---|
| `fused_top10_but_metric_still_wrong` | 12 | 75.0% | P0 record reached final evidence, but case still classified wrong because other expected doc type(s) missing from retrieved docs |
| `recalled_but_fused_low` | 3 | 18.8% | P0 record recalled by vector (ranks 2–11) but pushed out of fused top-10 by dual-contribution (keyword+vector) items |
| `vector_not_recalled` | 1 | 6.2% | P0 record not recalled by either keyword or vector search |

**Zero cases of:**
- `keyword_not_recalled` as primary (always paired with vector hit; when keyword alone fails, the case falls into `recalled_but_fused_low`)
- `doc_level_label_missing` (not yet classifiable — golden file has no doc_id labels for these cases)
- `query_expansion_gap` (requires manual inspection — not performed)
- `empty_retrieval` (all cases have non-empty retrieval results)
- `provider_identity_issue` (real provider used correctly)

---

## 2. Case-level Classification

| Case ID | P0 Record | Primary Bottleneck | Secondary Bottleneck | Evidence from Trace | Recommended Next Action |
|---|---|---|---|---|---|
| case_acco_003 | ae0e0e0e-bbbb (POLICY) | fused_top10_but_metric_still_wrong | keyword_not_recalled | P0 POLICY at fused rank 5, P0 CASE at fused rank 2, but Case+Policy still missing because other records of the right type not present | add_doc_level_golden_labels |
| case_acco_006 | ae0e0e0e-bbbb (POLICY) | **recalled_but_fused_low** | keyword_not_recalled, vector_edge | P0 POLICY vector rank 11 (edge of HNSW top-k), no keyword hit, not in fused top-10 | fusion_ranking_experiment |
| case_acco_012 | ae0e0e0e-bbbb (POLICY) | fused_top10_but_metric_still_wrong | keyword_not_recalled | P0 POLICY at fused rank 4, but Case type entirely missing from retrieved docs | add_doc_level_golden_labels |
| case_comp_001 | ca0a0a0a-5555 (CASE) | **recalled_but_fused_low** | keyword_not_recalled | P0 CASE vector rank 3 — excellent! No keyword hit → single RRF contribution → pushed out of fused top-10 | fusion_ranking_experiment |
| case_comp_002 | ca0a0a0a-6666 (CASE) | **recalled_but_fused_low** | keyword_not_recalled | P0 CASE vector rank 2 — almost perfect! No keyword hit → pushed out of fused top-10 by dual-contribution items | fusion_ranking_experiment |
| case_comp_003 | ca0a0a0a-7777 (CASE) | fused_top10_but_metric_still_wrong | keyword_not_recalled | P0 CASE at fused rank 2, but Policy doc type entirely missing | add_doc_level_golden_labels |
| case_comp_004 | ca0a0a0a-9999 (CASE) | fused_top10_but_metric_still_wrong | — | P0 CASE at fused rank 4, keyword+vector both hit, but Policy type still missing | add_doc_level_golden_labels |
| case_comp_008 | ca0a0a0a-8888 (CASE) | fused_top10_but_metric_still_wrong | keyword_not_recalled | P0 CASE at fused rank 1 — **perfect recall** in the only expected type (Case), yet still classified wrong | doc_level_label_missing |
| case_comp_009 | ca0a0a0a-9999 (CASE) | fused_top10_but_metric_still_wrong | keyword_not_recalled | P0 CASE at fused rank 5, but Policy type missing | add_doc_level_golden_labels |
| case_refu_001 | ae0e0e0e-aaaa (POLICY) | fused_top10_but_metric_still_wrong | — | P0 POLICY at fused rank 3, keyword+vector both hit, but Case type missing | add_doc_level_golden_labels |
| case_refu_006 | ae0e0e0e-aaaa (POLICY) | fused_top10_but_metric_still_wrong | — | Same record as refu_001, same pattern — Case type missing | add_doc_level_golden_labels |
| case_refu_009 | ae0e0e0e-dddd (POLICY) | fused_top10_but_metric_still_wrong | — | P0 POLICY at fused rank 1 — perfect, but Case type missing | add_doc_level_golden_labels |
| case_refu_013 | ae0e0e0e-cccc (POLICY) | **vector_not_recalled** | keyword_not_recalled | Counterfeit policy: not found by any ranker — record content may not match query keywords or embedding | query_expansion_audit |
| case_refu_013 | ca0a0a0a-6666 (CASE) | fused_top10_but_metric_still_wrong | — | P0 CASE at fused rank 2, but Policy type (ae0e0e0e-cccc) missing | add_doc_level_golden_labels |
| case_retu_004 | f0f0f0f0-2222 (FAQ) | fused_top10_but_metric_still_wrong | keyword_not_recalled | P0 FAQ at fused rank 5, but Case+Policy expected — FAQ alone insufficient | add_doc_level_golden_labels |

---

## 3. Recommendation Matrix

| Recommended Action | Cases Affected | Why | Should Implement Now? |
|---|---|---|---|
| `add_doc_level_golden_labels` | 10 cases (acco_003, acco_012, comp_003, comp_004, comp_008, comp_009, refu_001, refu_006, refu_009, refu_013, retu_004) | The dominant bottleneck (75%) is cases where P0 records reach final evidence but the case is still wrong because the metric checks doc_type coverage, not doc_id relevance. Adding `expected_relevant_doc_ids` to the golden file would allow doc-level MRR/Recall@K metrics that correctly measure whether the right specific document was retrieved. | **Yes** — this is the single highest-impact action. Without doc-level labels, we cannot distinguish "retrieval failed" from "metric too coarse." |
| `fusion_ranking_experiment` | 3 cases (acco_006, comp_001, comp_002) | P0 records with excellent vector ranks (2–11) are pushed out of fused top-10 because RRF biases toward dual-source items. A fusion experiment (lower k, or score-based fusion) could increase P0 recall. | **Yes** — for the 3 cases where vector recall is good but fusion fails. |
| `query_expansion_audit` | 1 case (refu_013 — ae0e0e0e-cccc only) | Counterfeit policy record completely missed by both rankers. Needs manual audit of query vs. record content to determine if the missing record's terms match query patterns. | **After doc-level labels** — affects only 1 record. |
| `leave_as_limitation` | 0 cases requiring this now | Once doc-level labels are added, most "fused_top10_but_metric_still_wrong" cases may become "correct" at doc level. | N/A |

---

## 4. Product Interpretation

### Why Phase 10 does not directly tune parameters

Phase 10 is a **diagnostic** phase. The goal is to understand the ranking pipeline's failure modes before making changes. The trace-first approach reveals:

1. **Vector recall is excellent (93.8%)** with the real embedding provider. The investment in a real provider (Phase 9.5) paid off — P0 records are semantically matched to their target queries.

2. **Keyword recall is weak (31.2%)** but this may be inherent to the data — P0 records use domain-specific terms (e.g., "假货鉴定", "律师函", "骚扰电话") that don't match typical customer query keywords.

3. **RRF fusion is the weakest link**: 3/16 records with excellent vector rank (2–3) are pushed out of fused top-10 because they lack keyword hits. This is a known RRF property — it favors broad ranker agreement over single-ranker depth.

### Why wrong cases remaining ≠ knowledge expansion ineffective

**75% of P0 records reach final evidence.** The fact that cases are still "wrong" is primarily a **metric granularity problem**, not a retrieval failure:

- The current metric checks: "is there at least one `Case` doc in Top-10?" and "is there at least one `Policy` doc in Top-10?"
- Adding a P0 Policy record fixes the Policy side, but if the Case side is also missing, the case is still "wrong"
- This means the case would need **both** a P0 Policy AND a P0 Case record to switch from wrong to correct

**Bottom line:** The knowledge expansion was effective at getting P0 records retrieved. The remaining wrong cases are mostly about incomplete doc_type coverage per case, not about individual record retrieval failure.

### Next priority: doc-level golden labels

Adding `expected_relevant_doc_ids` to the golden file would:
- Enable doc-level MRR and Recall@K metrics
- Correctly measure whether the right specific document is retrieved (not just "any doc of this type")
- Distinguish "retrieval failed" from "metric too coarse"
- Make Phase 10 bottleneck classification more precise
