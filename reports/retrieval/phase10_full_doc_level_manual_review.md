# Phase 10.7 — Full-Dataset Doc-Level Manual Review Report

*Generated at 2026-05-06 UTC*
*Part of Phase 10: Hybrid Retrieval Ranking Diagnosis*

## Purpose

Cases that could not be reliably auto-labeled with `expected_relevant_doc_ids`
due to insufficient knowledge coverage, ambiguous semantics, or edge-case status.

## Summary

| Metric | Value |
|---|---|
| Total eval cases | 101 |
| Auto-labeled with high confidence | 72 |
| Sent to manual review | 15 |
| Already labeled (P0) | 14 |

## Manual Review Cases

| Case ID | Reason | Candidate Doc IDs | Why Not Auto-labeled | Suggested Human Decision |
|---|---|---|---|---|
| case_edge_001 | Edge case: single-character text '退'. No meaningful retrieval possible. | (none) | Single character provides no semantic signal for doc_id mapping. | Leave empty — edge case with insufficient semantic content. |
| case_edge_002 | Edge case: very long mixed Chinese/English text. Complex multi-issue ticket (refund + complaint + technical). | (none) | Multiple overlapping issues make doc_id selection ambiguous. Requires human judgment to determine primary evidence. | Leave empty or label after human review of which issue is primary. |
| case_edge_003 | Edge case: special characters only. No semantic content. | (none) | Special characters provide no semantic signal for doc_id mapping. | Leave empty — edge case with no semantic content. |
| case_edge_004 | Edge case: Chinese with special characters only. No coherent semantic content. | (none) | Non-coherent text provides no signal for doc_id mapping. | Leave empty — edge case with no coherent semantic content. |
| case_edge_005 | Edge case: numbers and symbols only. No coherent semantic content. | (none) | Numbers and symbols provide no signal for doc_id mapping. | Leave empty — edge case with no semantic content. |
| case_logi_004 | Reschedule delivery — only POLICY match available, no FAQ specifically covers rescheduling. | a7777777-7777-7777-7777-777777777777 | Only POLICY a7777777 loosely covers delivery timing. No FAQ or CASE specifically about rescheduling. Low confidence. | Label with POLICY only or leave for human to decide if a broader label is appropriate. |
| case_logi_009 | International customs duties — only POLICY match available, no FAQ about international shipping. | a7777777-7777-7777-7777-777777777777 | Only POLICY broadly covers delivery. No FAQ about customs duties or international shipping. Low confidence. | Label with POLICY only or leave empty. Knowledge gap about international shipping. |
| case_othe_001 | Job/inquiry question about part-time客服 positions. No knowledge record covers HR/job inquiries. | (none) | No FAQ, Policy, or Case record covers job applications or recruitment. | Leave empty — this is outside the current knowledge domain. |
| case_othe_004 | Customer asks if platform has physical stores. No knowledge record about store locations. | (none) | No FAQ covers offline store information. | Leave empty — this is outside the current knowledge domain. |
| case_othe_005 | Customer asks about points balance. No FAQ about points/loyalty program. | (none) | No FAQ covers points balance inquiry. | Leave empty — this is outside the current knowledge domain. |
| case_othe_007 | Customer asks about WeChat group. No knowledge record about customer communication groups. | (none) | No FAQ covers WeChat groups or community channels. | Leave empty — this is outside the current knowledge domain. |
| case_othe_008 | Follow-up on packaging improvement suggestion. Suggestion/complaint, not a standard issue. | (none) | No FAQ covers packaging suggestions. Too ambiguous. | Leave empty — suggestion follow-up, not a standard retrieval scenario. |
| case_prod_003 | No FAQ/Policy about membership benefits. Multiple plausible docs but no clear primary evidence. | ffffffff-1111-1111-1111-111111111111 | Membership program is not covered by existing knowledge seed. Product consulting FAQ covers general product info, not membership-specific content. | Label with broadest FAQ or leave empty. Current knowledge seed lacks membership content. |
| case_tech_005 | Slow website loading — only POLICY match, no specific FAQ about website speed. | aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa | POLICY covers general tech support but no FAQ specifically addresses website speed. Single-doc label is weak. | Label with POLICY only. Adequate but not ideal. |
| case_tech_006 | Can't select address during checkout — only POLICY match, no specific FAQ. | aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa | POLICY covers general tech support. No FAQ about address selection bug. Low confidence. | Label with POLICY only. Adequate but not ideal. |

## Categories of Manual Review Cases

### Edge Cases (5)
case_edge_001 through case_edge_005 — Single chars, special chars, numbers-only text.
No semantic content for doc_id mapping.

### Knowledge Gap Cases (4)
- **case_othe_001**: Job inquiries (no HR knowledge)
- **case_othe_004**: Physical store locations (no offline store knowledge)
- **case_othe_005**: Points balance (no loyalty program knowledge)
- **case_othe_007**: WeChat group inquiries (no community channel knowledge)

### Ambiguous Cases (4)
- **case_othe_008**: Packaging suggestion follow-up — not a standard retrieval issue
- **case_edge_002**: Multi-issue ticket (refund + complaint + technical) — ambiguous primary evidence
- **case_prod_003**: Membership benefits — knowledge seed has no membership content
- **case_logi_004**: Reschedule delivery — only weak POLICY match, no FAQ
- **case_logi_009**: International customs duties — only weak POLICY match

### Low-Confidence Auto-Label (2)
- **case_tech_005**: Slow website — labeled with POLICY only, but weak match
- **case_tech_006**: Address selection — labeled with POLICY only, but weak match

## Impact on Evaluation

Manual review cases will remain unlabeled (`expected_relevant_doc_ids` empty).
The doc-level evaluation will skip these cases (backward compatible behavior).

**Recommendation**: Add knowledge seed records for the 4 knowledge gap cases
if full coverage is needed. Edge cases can remain unlabeled permanently.
