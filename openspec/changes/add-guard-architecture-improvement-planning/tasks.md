# Tasks: Guard Architecture Improvement — Granular Failure Taxonomy

## Task List

- [x] 14.1: Planning and OpenSpec spec (this phase)
  - Create proposal.md, design.md, tasks.md, spec.md
  - Run OpenSpec strict and --all validation
  - No runtime code changes

- [x] 14.2: Guard Taxonomy Data Model
  - Add `GuardFailureType` enum to `drafting/schemas.py` or `drafting/claim_guard.py`
  - Extend `GuardResult` with `failure_reasons: list[GuardFailureType]`
  - Backward compatible: existing boolean fields unchanged
  - Add unit tests for new taxonomy

- [x] 14.2.1: Guard Taxonomy Cleanup (Phase 14.2.1)
  - Fix enum member canonical name to `UNCITED_SUBSTANTIVE_CLAIM` (was misspelled UNCUTED)
  - Keep serialized value stable as "UNCITED_SUBSTANTIVE_CLAIM" (historical consistency)
  - Change `failure_reasons` to failure-only (remove EVIDENCE_INSUFFICIENT_FALLBACK from guard_passed=True cases)
  - safe fallback signal deferred to future guard_signals/reporting phase
  - No guard weakening, no human review reduction
  - Full quality gate: 1087 unit + 146 integration, 0 skipped, coverage >= 70%

- [ ] 14.3: Safe Language Classifier
  - Implement `check_safe_escalation_language()` function
  - Detect safe escalation keywords: 人工处理, 转人工客服, 需要人工审核, 人工审查, 升级处理
  - Implement `check_manual_review_acknowledgement()` function
  - Detect manual review keywords: 人工审核, 需人工 review, 人工确认
  - Add unit tests for both functions

- [x] 14.4: Claim Guard Integration
  - Wire `failure_reasons` population into `check_claim_guard()`
  - Add `MISSING_RISK_ESCALATION` when `risk_flags_respected=False` and escalation keywords absent
  - Add `EVIDENCE_INSUFFICIENT_FALLBACK` when draft matches safe fallback text
  - Preserve existing boolean field logic
  - Add unit tests for taxonomy integration

- [ ] 14.5: Evaluation Runner Extension
  - Extend `DraftEvaluationRow` with `guard_failure_types: list[str]`
  - Update comparison runner to extract failure_reasons
  - Re-run 25-case comparison with FakeLLMProvider
  - Report per-failure-type pass rate

- [ ] 14.6: Reviewer Console and Portfolio Updates
  - Update reviewer console to display guard failure taxonomy
  - Update metrics dashboard with per-type breakdown
  - Update Phase 13.10 report with taxonomy analysis
  - No new portfolio claims

- [ ] 14.7: Final Validation and Archive
  - Full quality gate: 1078 unit + 146 integration, 0 skipped, coverage >= 70%
  - Ruff clean, OpenSpec --all pass, secret scan clean
  - Archive OpenSpec change
  - Update harness docs

## Dependencies

- 14.2 must complete before 14.3, 14.4
- 14.3, 14.4 must complete before 14.5
- 14.5 must complete before 14.6
- 14.6 must complete before 14.7

## Exit Criteria

- Guard taxonomy added without weakening existing guard checks
- `guard_passed` logic unchanged
- Human review requirements unchanged
- No-auto-send invariant preserved
- Per-failure-type metrics available for Phase 13.10 cases
- Full quality gate: 1078 unit + 146 integration, 0 skipped, coverage >= 70%
- No API key in tracked files
