# Evaluation Report

**Generated at:** 2026-05-04T10:02:34.661825+00:00

## Dataset Summary

| Field | Value |
|---|---|
| Total cases | 101 |
| Tickets file | `data/eval/tickets_eval.csv` |
| Golden file | `data/eval/golden_expectations.csv` |
| Predictions file | `pipeline (generated from local TicketPilot pipeline)` |
| Prediction mode | pipeline (local) |
| Mismatches found | 306 |

## Aggregate Metrics

| Metric | Value |
|---|---|
| Intent accuracy | 53.5% |
| Severity accuracy | 54.5% |
| Must-human-review accuracy | 53.5% |
| Evidence doc type recall | 43.2% |
| Fallback correctness | 90.1% |
| No-auto-send compliance | 100.0% |

## Risk Flag Metrics (Micro-Averaged)

| Metric | Value |
|---|---|
| Precision | 33.3% |
| Recall | 27.0% |
| F1 | 29.8% |

## Mismatch Summary

| Case ID | Metric | Expected | Predicted |
|---|---|---|---|
| case_acco_001 | evidence_doc_type_recall | Case,FAQ,Policy | CASE,FAQ,POLICY |
| case_acco_001 | must_human_review_accuracy | True | False |
| case_acco_001 | risk_flags | account_security_risk |  |
| case_acco_001 | severity_accuracy | HIGH | LOW |
| case_acco_002 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_acco_002 | must_human_review_accuracy | True | False |
| case_acco_002 | risk_flags | account_security_risk |  |
| case_acco_002 | severity_accuracy | MEDIUM | LOW |
| case_acco_003 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_acco_003 | intent_accuracy | account_issue | other |
| case_acco_003 | risk_flags | complaint_risk,privacy_risk | low_confidence,privacy_risk |
| case_acco_003 | severity_accuracy | HIGH | LOW |
| case_acco_004 | evidence_doc_type_recall | Case,FAQ,Policy | CASE,FAQ,POLICY |
| case_acco_004 | intent_accuracy | account_issue | logistics |
| case_acco_004 | risk_flags | account_security_risk,privacy_risk |  |
| case_acco_004 | severity_accuracy | HIGH | LOW |
| case_acco_005 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_acco_005 | fallback_correctness | True | False |
| case_acco_005 | risk_flags | insufficient_evidence | privacy_risk |
| case_acco_005 | severity_accuracy | MEDIUM | LOW |
| case_acco_006 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_acco_006 | intent_accuracy | account_issue | other |
| case_acco_006 | risk_flags | account_security_risk,privacy_risk | low_confidence |
| case_acco_006 | severity_accuracy | HIGH | LOW |
| case_acco_007 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_acco_007 | intent_accuracy | account_issue | other |
| case_acco_007 | risk_flags |  | low_confidence |
| case_acco_007 | severity_accuracy | MEDIUM | LOW |
| case_acco_008 | evidence_doc_type_recall | Case,FAQ,Policy | CASE,FAQ,POLICY |
| case_acco_008 | severity_accuracy | HIGH | LOW |
| case_acco_009 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_acco_009 | fallback_correctness | True | False |
| case_acco_009 | risk_flags | complaint_risk,insufficient_evidence | policy_conflict |
| case_acco_009 | severity_accuracy | MEDIUM | LOW |
| case_acco_010 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_acco_011 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_acco_011 | intent_accuracy | account_issue | other |
| case_acco_011 | must_human_review_accuracy | False | True |
| case_acco_011 | risk_flags |  | low_confidence,privacy_risk |
| case_acco_012 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_acco_012 | intent_accuracy | account_issue | other |
| case_acco_012 | risk_flags | legal_risk,privacy_risk | low_confidence,privacy_risk |
| case_acco_012 | severity_accuracy | HIGH | LOW |
| case_acco_013 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_acco_013 | must_human_review_accuracy | False | True |
| case_acco_013 | risk_flags |  | privacy_risk |
| case_acco_014 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_acco_014 | risk_flags | account_security_risk,legal_risk,privacy_risk | privacy_risk |
| case_acco_014 | severity_accuracy | HIGH | LOW |
| case_acco_015 | evidence_doc_type_recall | Case,FAQ,Policy | CASE,FAQ,POLICY |
| case_acco_015 | intent_accuracy | account_issue | complaint |
| case_acco_015 | risk_flags | account_security_risk,complaint_risk | complaint_risk |
| case_acco_015 | severity_accuracy | MEDIUM | LOW |
| case_comp_001 | evidence_doc_type_recall | Case | CASE,FAQ,POLICY |
| case_comp_001 | severity_accuracy | MEDIUM | LOW |
| case_comp_002 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_comp_002 | risk_flags | complaint_risk,legal_risk | complaint_risk |
| case_comp_002 | severity_accuracy | HIGH | LOW |
| case_comp_003 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_comp_003 | intent_accuracy | complaint | other |
| case_comp_003 | risk_flags | compensation_risk,complaint_risk | low_confidence |
| case_comp_003 | severity_accuracy | MEDIUM | LOW |
| case_comp_004 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_comp_004 | intent_accuracy | complaint | other |
| case_comp_004 | risk_flags | compensation_risk,complaint_risk,legal_risk | compensation_risk,legal_risk |
| case_comp_005 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_comp_005 | intent_accuracy | complaint | other |
| case_comp_005 | risk_flags | complaint_risk,legal_risk,privacy_risk | low_confidence,privacy_risk |
| case_comp_005 | severity_accuracy | HIGH | LOW |
| case_comp_006 | evidence_doc_type_recall | Case | CASE,FAQ,POLICY |
| case_comp_006 | severity_accuracy | MEDIUM | LOW |
| case_comp_007 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_comp_007 | intent_accuracy | complaint | return_exchange |
| case_comp_007 | risk_flags | compensation_risk,complaint_risk | compensation_risk |
| case_comp_007 | severity_accuracy | MEDIUM | LOW |
| case_comp_008 | evidence_doc_type_recall | Case | CASE,FAQ,POLICY |
| case_comp_008 | intent_accuracy | complaint | other |
| case_comp_008 | risk_flags | complaint_risk | low_confidence |
| case_comp_008 | severity_accuracy | MEDIUM | LOW |
| case_comp_009 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_comp_009 | intent_accuracy | complaint | other |
| case_comp_009 | risk_flags | compensation_risk,complaint_risk,policy_conflict | low_confidence |
| case_comp_009 | severity_accuracy | HIGH | LOW |
| case_comp_011 | intent_accuracy | complaint | other |
| case_comp_011 | must_human_review_accuracy | False | True |
| case_comp_011 | risk_flags |  | low_confidence |
| case_comp_012 | evidence_doc_type_recall | Case,FAQ | CASE,FAQ,POLICY |
| case_comp_013 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_comp_013 | intent_accuracy | complaint | other |
| case_comp_013 | risk_flags | complaint_risk,legal_risk,privacy_risk | low_confidence,privacy_risk |
| case_comp_013 | severity_accuracy | HIGH | LOW |
| case_edge_001 | fallback_correctness | True | False |
| case_edge_001 | intent_accuracy | refund | other |
| case_edge_001 | risk_flags | insufficient_evidence | insufficient_evidence,low_confidence |
| case_edge_002 | evidence_doc_type_recall | Case,Policy |  |
| case_edge_002 | fallback_correctness | False | True |
| case_edge_002 | risk_flags | compensation_risk,complaint_risk,policy_conflict | complaint_risk,insufficient_evidence |
| case_edge_002 | severity_accuracy | MEDIUM | LOW |
| case_edge_005 | risk_flags | insufficient_evidence | insufficient_evidence,low_confidence |
| case_logi_001 | evidence_doc_type_recall | Case,FAQ | CASE,FAQ,POLICY |
| case_logi_002 | evidence_doc_type_recall | Case,FAQ | CASE,FAQ,POLICY |
| case_logi_002 | fallback_correctness | True | False |
| case_logi_002 | must_human_review_accuracy | True | False |
| case_logi_002 | risk_flags | insufficient_evidence |  |
| case_logi_002 | severity_accuracy | MEDIUM | LOW |
| case_logi_003 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_logi_003 | intent_accuracy | logistics | other |
| case_logi_003 | must_human_review_accuracy | False | True |
| case_logi_003 | risk_flags |  | low_confidence |
| case_logi_005 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_logi_005 | risk_flags | compensation_risk |  |
| case_logi_005 | severity_accuracy | MEDIUM | LOW |
| case_logi_006 | evidence_doc_type_recall | Case,FAQ | CASE,FAQ,POLICY |
| case_logi_006 | fallback_correctness | True | False |
| case_logi_006 | must_human_review_accuracy | True | False |
| case_logi_006 | risk_flags | insufficient_evidence |  |
| case_logi_006 | severity_accuracy | MEDIUM | LOW |
| case_logi_007 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_logi_007 | intent_accuracy | logistics | other |
| case_logi_007 | must_human_review_accuracy | False | True |
| case_logi_007 | risk_flags |  | low_confidence |
| case_logi_008 | evidence_doc_type_recall | Case | CASE,FAQ |
| case_logi_008 | must_human_review_accuracy | True | False |
| case_logi_008 | risk_flags | complaint_risk |  |
| case_logi_008 | severity_accuracy | MEDIUM | LOW |
| case_logi_009 | evidence_doc_type_recall | FAQ,Policy | FAQ,POLICY |
| case_logi_009 | must_human_review_accuracy | True | False |
| case_logi_009 | risk_flags | policy_conflict |  |
| case_logi_010 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_logi_010 | intent_accuracy | logistics | other |
| case_logi_010 | risk_flags | compensation_risk,complaint_risk | low_confidence |
| case_logi_010 | severity_accuracy | MEDIUM | LOW |
| case_logi_011 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_logi_011 | intent_accuracy | logistics | other |
| case_logi_011 | risk_flags | compensation_risk,complaint_risk | low_confidence |
| case_logi_011 | severity_accuracy | MEDIUM | LOW |
| case_othe_001 | must_human_review_accuracy | False | True |
| case_othe_001 | risk_flags |  | low_confidence |
| case_othe_002 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_othe_002 | risk_flags | policy_conflict | low_confidence |
| case_othe_003 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_othe_003 | must_human_review_accuracy | False | True |
| case_othe_003 | risk_flags |  | low_confidence |
| case_othe_004 | must_human_review_accuracy | False | True |
| case_othe_004 | risk_flags |  | low_confidence |
| case_othe_005 | must_human_review_accuracy | False | True |
| case_othe_005 | risk_flags |  | low_confidence |
| case_othe_006 | intent_accuracy | other | product_consulting |
| case_othe_007 | must_human_review_accuracy | False | True |
| case_othe_007 | risk_flags |  | low_confidence |
| case_othe_008 | must_human_review_accuracy | False | True |
| case_othe_008 | risk_flags |  | low_confidence |
| case_othe_009 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_othe_009 | risk_flags | compensation_risk,policy_conflict | low_confidence |
| case_othe_009 | severity_accuracy | MEDIUM | LOW |
| case_othe_010 | evidence_doc_type_recall | Case,FAQ,Policy | CASE,FAQ,POLICY |
| case_othe_010 | fallback_correctness | True | False |
| case_othe_010 | risk_flags | insufficient_evidence,policy_conflict | low_confidence |
| case_othe_010 | severity_accuracy | MEDIUM | LOW |
| case_othe_011 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_othe_011 | risk_flags | complaint_risk | low_confidence |
| case_othe_011 | severity_accuracy | MEDIUM | LOW |
| case_othe_012 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_othe_012 | risk_flags | policy_conflict | low_confidence |
| case_othe_012 | severity_accuracy | MEDIUM | LOW |
| case_othe_013 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_othe_013 | risk_flags | complaint_risk,policy_conflict | low_confidence |
| case_othe_013 | severity_accuracy | MEDIUM | LOW |
| case_prod_001 | intent_accuracy | product_consulting | other |
| case_prod_001 | must_human_review_accuracy | False | True |
| case_prod_001 | risk_flags |  | low_confidence |
| case_prod_002 | intent_accuracy | product_consulting | other |
| case_prod_002 | must_human_review_accuracy | False | True |
| case_prod_002 | risk_flags |  | low_confidence |
| case_prod_003 | intent_accuracy | product_consulting | other |
| case_prod_003 | must_human_review_accuracy | False | True |
| case_prod_003 | risk_flags |  | low_confidence |
| case_prod_004 | intent_accuracy | product_consulting | other |
| case_prod_004 | must_human_review_accuracy | False | True |
| case_prod_004 | risk_flags |  | low_confidence |
| case_prod_005 | intent_accuracy | product_consulting | other |
| case_prod_005 | must_human_review_accuracy | False | True |
| case_prod_005 | risk_flags |  | low_confidence |
| case_prod_006 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_prod_006 | intent_accuracy | product_consulting | other |
| case_prod_006 | must_human_review_accuracy | False | True |
| case_prod_006 | risk_flags |  | low_confidence |
| case_prod_007 | intent_accuracy | product_consulting | other |
| case_prod_007 | must_human_review_accuracy | False | True |
| case_prod_007 | risk_flags |  | low_confidence |
| case_prod_008 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_prod_008 | intent_accuracy | product_consulting | other |
| case_prod_008 | must_human_review_accuracy | False | True |
| case_prod_008 | risk_flags |  | low_confidence |
| case_refu_001 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_refu_001 | intent_accuracy | refund | complaint |
| case_refu_001 | risk_flags | complaint_risk,low_confidence | complaint_risk |
| case_refu_001 | severity_accuracy | MEDIUM | LOW |
| case_refu_002 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_refu_002 | must_human_review_accuracy | False | True |
| case_refu_003 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_refu_003 | risk_flags | complaint_risk,policy_conflict |  |
| case_refu_003 | severity_accuracy | MEDIUM | LOW |
| case_refu_004 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_refu_004 | intent_accuracy | refund | other |
| case_refu_004 | must_human_review_accuracy | False | True |
| case_refu_004 | risk_flags |  | low_confidence |
| case_refu_005 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_refu_005 | risk_flags | complaint_risk |  |
| case_refu_006 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_refu_006 | intent_accuracy | refund | complaint |
| case_refu_006 | risk_flags | compensation_risk,complaint_risk | complaint_risk |
| case_refu_006 | severity_accuracy | MEDIUM | LOW |
| case_refu_007 | intent_accuracy | refund | logistics |
| case_refu_007 | must_human_review_accuracy | False | True |
| case_refu_008 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_refu_008 | risk_flags | compensation_risk |  |
| case_refu_009 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_refu_009 | risk_flags | complaint_risk,legal_risk | legal_risk |
| case_refu_010 | evidence_doc_type_recall | Case,FAQ,Policy | CASE,FAQ,POLICY |
| case_refu_010 | intent_accuracy | refund | return_exchange |
| case_refu_010 | must_human_review_accuracy | False | True |
| case_refu_011 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_refu_011 | must_human_review_accuracy | False | True |
| case_refu_012 | evidence_doc_type_recall | Case,FAQ,Policy | CASE,FAQ,POLICY |
| case_refu_012 | fallback_correctness | True | False |
| case_refu_012 | intent_accuracy | refund | logistics |
| case_refu_012 | must_human_review_accuracy | True | False |
| case_refu_012 | risk_flags | complaint_risk,insufficient_evidence |  |
| case_refu_012 | severity_accuracy | MEDIUM | LOW |
| case_refu_013 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_refu_013 | risk_flags | compensation_risk,policy_conflict | compensation_risk |
| case_refu_013 | severity_accuracy | HIGH | LOW |
| case_refu_014 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_refu_014 | intent_accuracy | refund | other |
| case_refu_014 | must_human_review_accuracy | False | True |
| case_refu_014 | risk_flags |  | low_confidence |
| case_refu_015 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_refu_015 | risk_flags | compensation_risk,complaint_risk,legal_risk |  |
| case_refu_015 | severity_accuracy | HIGH | LOW |
| case_refu_016 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_refu_016 | intent_accuracy | refund | other |
| case_refu_016 | risk_flags | policy_conflict | low_confidence |
| case_refu_016 | severity_accuracy | MEDIUM | LOW |
| case_retu_001 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_retu_001 | intent_accuracy | return_exchange | other |
| case_retu_001 | must_human_review_accuracy | False | True |
| case_retu_001 | risk_flags |  | low_confidence |
| case_retu_002 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_retu_002 | intent_accuracy | return_exchange | other |
| case_retu_002 | must_human_review_accuracy | False | True |
| case_retu_002 | risk_flags |  | low_confidence |
| case_retu_003 | evidence_doc_type_recall | Case,FAQ,Policy | CASE,FAQ,POLICY |
| case_retu_003 | must_human_review_accuracy | True | False |
| case_retu_003 | risk_flags | complaint_risk |  |
| case_retu_004 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_retu_004 | risk_flags | compensation_risk,policy_conflict | compensation_risk |
| case_retu_004 | severity_accuracy | MEDIUM | LOW |
| case_retu_005 | evidence_doc_type_recall | Case,FAQ,Policy | CASE,FAQ,POLICY |
| case_retu_006 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_retu_006 | must_human_review_accuracy | True | False |
| case_retu_006 | risk_flags | compensation_risk,complaint_risk |  |
| case_retu_006 | severity_accuracy | MEDIUM | LOW |
| case_retu_007 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_retu_007 | intent_accuracy | return_exchange | logistics |
| case_retu_007 | must_human_review_accuracy | False | True |
| case_retu_008 | evidence_doc_type_recall | Policy | CASE,FAQ,POLICY |
| case_retu_008 | must_human_review_accuracy | True | False |
| case_retu_008 | risk_flags | policy_conflict |  |
| case_retu_009 | evidence_doc_type_recall | FAQ,Policy | CASE,FAQ,POLICY |
| case_retu_009 | intent_accuracy | return_exchange | other |
| case_retu_009 | must_human_review_accuracy | False | True |
| case_retu_009 | risk_flags |  | low_confidence |
| case_retu_010 | evidence_doc_type_recall | Case,Policy | CASE,FAQ,POLICY |
| case_retu_010 | must_human_review_accuracy | True | False |
| case_retu_010 | risk_flags | complaint_risk,policy_conflict |  |
| case_retu_010 | severity_accuracy | MEDIUM | LOW |
| case_retu_011 | evidence_doc_type_recall | Case | CASE,FAQ,POLICY |
| case_retu_011 | must_human_review_accuracy | True | False |
| case_retu_011 | risk_flags | complaint_risk |  |
| case_retu_011 | severity_accuracy | MEDIUM | LOW |
| case_tech_001 | intent_accuracy | technical_issue | other |
| case_tech_001 | must_human_review_accuracy | False | True |
| case_tech_001 | risk_flags |  | low_confidence |
| case_tech_002 | intent_accuracy | technical_issue | other |
| case_tech_002 | must_human_review_accuracy | False | True |
| case_tech_002 | risk_flags |  | low_confidence |
| case_tech_003 | evidence_doc_type_recall | Case,FAQ,Policy | CASE,FAQ,POLICY |
| case_tech_003 | fallback_correctness | True | False |
| case_tech_003 | must_human_review_accuracy | True | False |
| case_tech_003 | risk_flags | insufficient_evidence,policy_conflict |  |
| case_tech_003 | severity_accuracy | MEDIUM | LOW |
| case_tech_004 | intent_accuracy | technical_issue | other |
| case_tech_004 | must_human_review_accuracy | False | True |
| case_tech_004 | risk_flags |  | low_confidence |
| case_tech_005 | intent_accuracy | technical_issue | other |
| case_tech_005 | must_human_review_accuracy | False | True |
| case_tech_005 | risk_flags |  | low_confidence |
| case_tech_006 | intent_accuracy | technical_issue | other |
| case_tech_006 | must_human_review_accuracy | False | True |
| case_tech_006 | risk_flags |  | low_confidence |
| case_tech_008 | evidence_doc_type_recall | Case,FAQ,Policy | CASE,FAQ,POLICY |
| case_tech_008 | fallback_correctness | True | False |
| case_tech_008 | intent_accuracy | technical_issue | other |
| case_tech_008 | risk_flags | insufficient_evidence,policy_conflict | low_confidence |
| case_tech_008 | severity_accuracy | MEDIUM | LOW |

## Limitations

- **Small deterministic seed dataset**: This evaluation uses a small set of curated deterministic seed data. Results are not statistically significant and should not be used to claim real-world performance.
- **No real embedding provider**: The current evaluation uses fake embeddings. Evidence retrieval metrics will change when a real embedding provider is integrated unless pipeline mode is added later.
- **Not real-world performance**: This report reflects offline evaluation on synthetic/golden data only. It does not represent production behavior.