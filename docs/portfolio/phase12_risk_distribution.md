# Phase 12 Risk Distribution Display

**Scope**: Local demo / portfolio prototype — offline fixture-based analysis
**Generated**: 2026-05-07
**Sources**: `reports/eval/phase12_llm_provider_comparison_rows.json`, `src/ticketpilot/risk/rules.py`

---

## 1. Risk Flag Distribution (Phase 12, 25-Case Fixture Set)

| Risk Flag | Cases | % of Set | Triggers Human Review? |
|-----------|-------|----------|------------------------|
| ordinary_product_consulting | 3 | 12% | No |
| refund | 2 | 8% | No |
| return_exchange | 2 | 8% | No |
| logistics | 2 | 8% | No |
| complaint | 2 | 8% | No |
| privacy_risk | 2 | 8% | **Yes** |
| account_security_risk | 2 | 8% | **Yes** |
| legal_complaint | 2 | 8% | **Yes** |
| compensation_risk | 2 | 8% | **Yes** |
| evidence_insufficient | 2 | 8% | No |
| policy_conflict | 2 | 8% | No |
| technical_issue | 2 | 8% | No |

**Source**: `phase12_llm_provider_comparison_rows.json` — case `scenario` field mapped to risk type.

---

## 2. Human Review Trigger Distribution (Phase 12, 25 Cases)

| Provider | Total Cases | Human Review Cases | Rate | Cases |
|----------|-------------|-------------------|------|-------|
| FakeLLMProvider | 25 | 8 | 32% | p12_011, p12_012, p12_013, p12_014, p12_015, p12_016, p12_017, p12_018 |
| OpenAICompatibleProvider | 25 | 8 | 32% | same 8 cases |

**Identical triggers**: Both providers produced human review on the same 8 cases. This confirms the risk-rule wiring is provider-agnostic.

---

## 3. Human Review Trigger Logic

The current rule system triggers human review for:

| Condition | Effect |
|-----------|--------|
| `severity = HIGH` | `must_human_review = true` |
| `unsupported_claims = true` | `must_human_review = true` |
| `escalation_reason` set | `must_human_review = true` |
| `draft_citation_validation.is_valid = false` | `must_human_review = true` |
| `draft_citation_validation.missing_citation_required = true` | `must_human_review = true` |
| `draft_citation_validation.uncited_claims = true` | `must_human_review = true` |
| `claim_guard.guard_passed = false` | `escalation_reason` set, `must_human_review = true` |

**Source**: `src/ticketpilot/drafting/generator.py`, `src/ticketpilot/drafting/claim_guard.py`

---

## 4. Risk Type Explanations

### complaint_risk
**Pattern**: Customer expresses dissatisfaction or threatens escalation without legal language.
**Current handling**: MEDIUM severity, draft generated with citations, no mandatory human review.
**Rationale**: Complaints without legal threats can often be handled with policy-grounded responses.

### compensation_risk
**Pattern**: Customer requests monetary compensation, refund promises, or states financial loss.
**Current handling**: HIGH severity when combined with other flags; triggers human review.
**Rationale**: Compensation promises have direct financial implications; require human judgment.

### privacy_risk
**Pattern**: Customer reports data breach, unauthorized access, or privacy concerns.
**Current handling**: HIGH severity, human review mandatory.
**Rationale**: Privacy issues have regulatory implications (GDPR, Chinese PIPL); require human escalation.

### account_security_risk
**Pattern**: Customer reports unauthorized login, account takeover, or security breach.
**Current handling**: HIGH severity, human review mandatory.
**Rationale**: Account security issues require verification before any action; automated responses could cause harm.

### legal_risk
**Pattern**: Customer mentions lawyers, legal action, consumer protection agencies, or regulatory bodies.
**Current handling**: HIGH severity (always), human review mandatory.
**Rationale**: Legal threats require escalation to appropriate channels; any automated response could worsen the situation.

### insufficient_evidence
**Pattern**: Retrieval returns fewer than the minimum evidence threshold.
**Current handling**: Flag set, draft may still be generated, human review depends on severity.
**Rationale**: Low-evidence drafts may be incomplete or inaccurate; human review provides a safety net.

### low_confidence
**Pattern**: Classification or risk assessment confidence below threshold.
**Current handling**: Flag set, human review may be triggered depending on severity.
**Rationale**: Low confidence signals uncertainty; human review catches errors.

### policy_conflict
**Pattern**: Customer request conflicts with known policy.
**Current handling**: Flag set, draft may acknowledge the conflict, human review may be needed.
**Rationale**: Policy conflicts require human judgment on exception handling.

---

## 5. Data Limitations

**Limitation**: Phase 12 risk distribution is based on 25 synthetic cases. Real customer service tickets would likely have different risk distributions.

**Limitation**: Phase 12 cases are labeled with a single `scenario` type, but real tickets often have multiple concurrent risk flags (e.g., refund + complaint + legal).

**Proposed next step**: Add 5–10 multi-flag fixture cases to test the concurrent risk handling.

**Proposed next step**: Measure the distribution of concurrent risk flags in the full 101-case retrieval evaluation fixture set, not just the 25-case draft fixture.
