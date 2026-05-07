# Phase 12 Error and Limitation Analysis

**Scope**: Local demo / portfolio prototype — offline evaluation
**Generated**: 2026-05-07

---

## 1. Retrieval Errors

### 1.1 Zero-Hit Cases

**Symptom**: 9 cases have no expected document IDs found in the top-10 retrieval results.

**Likely root causes**:
- Query language does not match document vocabulary
- Domain-specific terms not represented in embeddings
- RRF fusion penalizes cases where keyword and vector disagree

**System response**: Cases are flagged in `wrong_case_recheck` report. Zero-hit cases are candidates for query expansion or knowledge addition.

**Remaining limitation**: Zero-hit analysis is based on a 86-case labeled subset of 101 synthetic tickets. The 15 unlabeled cases may include additional zero-hit cases.

**Next improvement**: Audit query vocabulary coverage; consider query expansion techniques.

---

### 1.2 Partial-Hit Cases

**Symptom**: 32 cases have some but not all expected document IDs found in top-10.

**Likely root causes**:
- RRF fusion ranking places some relevant docs beyond position 10
- Vector recall strong but keyword mismatch causes fusion score drop
- Some docs in the expected set are semantically less similar than non-relevant docs

**System response**: Partial-hit cases are classified as `cases_partial_hit` in the metrics. The 32 cases represent cases where retrieval found some relevant content but not all.

**Remaining limitation**: RRF parameter tuning (k=60) was not systematically optimized. The current value is a reasonable default but not validated.

**Next improvement**: Experiment with RRF k values; measure impact on partial-hit rate.

---

### 1.3 Doc-Type vs Doc-ID Metric Granularity Issue

**Symptom**: Doc-Type Recall@10 = 59.4%, Doc-ID Recall@10 = 91.9%. The 32.5 percentage point gap is almost entirely explained by metric granularity (41 cases marked "wrong" at doc-type level were actually correct at doc-id level).

**Likely root causes**:
- Multi-chunk documents share the same doc_type but different chunk_ids
- Doc-type evaluation counted a case as "wrong" if any expected chunk was missing from the doc-type set
- Doc-id evaluation correctly identifies that the right document was retrieved even if not all chunks were found

**System response**: This was diagnosed in Phase 10 and confirmed as a metric design issue, not a retrieval quality issue. 78% of doc-type "wrong" cases (32/41) were reclassified as doc-id found.

**Remaining limitation**: The 9 genuinely wrong cases still need investigation. These include 5 edge cases (case_edge_001–005) and 4 domain cases (case_comp_001, case_comp_002, case_logi_010).

**Next improvement**: Investigate the 9 remaining misses; consider domain-specific knowledge addition or query expansion.

---

## 2. Draft Generation Errors

### 2.1 Citation Validation Errors

**Symptom**: Draft may cite evidence IDs that do not exist in the evidence candidate list, cite the same evidence multiple times, or omit citations for substantively claimed content.

**System response**:
- `DraftCitationValidationResult` validates cited_evidence_ids against available evidence
- `CitationValidator` checks for invalid IDs, duplicates, and missing citations
- Validation failure forces `must_human_review = true`
- Source: `src/ticketpilot/drafting/draft_citation_validator.py`

**Remaining limitation**: Phase 12 provider comparison did not include per-case citation validation audit. Citation validation exists in the codebase but was not exercised in the Phase 12 fixture run.

**Next improvement**: Add citation validation metrics to Phase 12 comparison runner; audit whether cited IDs match evidence content.

---

### 2.2 Claim Guard Errors

**Symptom**: Draft may contain unsupported claims (statements not grounded in cited evidence) or forbidden promises (e.g., guaranteed refunds, assured compensation).

**System response**:
- `ClaimGuard` checks: citation coverage, uncited claims, forbidden promises (9 regex patterns), evidence sufficiency, risk acknowledgment
- `GuardResult` captures: guard_passed, has_forbidden_promise, has_uncited_claims, etc.
- Guard failure sets `escalation_reason` and forces human review
- Source: `src/ticketpilot/drafting/claim_guard.py`

**Phase 13 investigation**: Guard pass rate was 0% in initial Phase 13 run. Root cause identified:
- FakeLLMProvider template used `[N]` numeric markers (`[1]`, `[2]`) instead of `[UUID]` chunk_id markers
- Claim guard's `_extract_chunk_ids()` only recognizes `[UUID]` format
- Draft had 0 `[UUID]` references → `has_uncited_claims = True` → guard failed
- Citation validation passed because `cited_evidence_ids` (UUID list) was correct — only the text markers were wrong

**Fix applied** (Phase 13.8): Updated FakeLLMProvider to use `[{ev.chunk_id}]` instead of `[{i}]` in draft text.
After fix: guard pass rate = 68% (17/25). The remaining 8 failures are all HIGH-severity cases
(privacy_risk, account_security_risk, legal_risk, compensation_risk) where FakeLLMProvider
template does not include escalation acknowledgment language — correctly failing risk_flags_respected check.

**Result interpretation**:
- FakeLLMProvider validates pipeline mechanics, not guard-compliant draft quality
- guard_pass_rate=68% for FakeLLMProvider reflects template limitations, not a guard bug
- Real provider output should be evaluated separately when env is configured
- No auto-send; human review remains required for all HIGH-severity cases

**Remaining limitation**: Real provider guard pass rate unknown — requires .env.local configuration.

**Next improvement**: Run extended Phase 13 runner with real provider to get per-provider guard metrics.

---

### 2.3 Insufficient Evidence Fallback

**Symptom**: When no evidence candidates are retrieved, the system must still produce a draft (or safe fallback).

**System response**:
- FakeLLMProvider safe fallback: returns a structured draft with `must_human_review=true` and no citations
- Real provider: prompt instructions guide the model to acknowledge evidence limitations
- `evidence_insufficient` risk flag set by risk assessor

**Remaining limitation**: Insufficient evidence fallback was not specifically tested in Phase 12 (all 25 cases produced evidence candidates). Real-world cases with no evidence may produce different output quality.

**Next improvement**: Add 3–5 no-evidence fixture cases to the comparison set.

---

### 2.4 Provider Invalid JSON / Network Error Fallback

**Symptom**: Real provider API may return non-JSON response or fail to respond.

**System response**:
- `OpenAICompatibleProvider` wraps API calls with try/except
- JSON parsing errors are caught and logged
- Network errors propagate — no silent fallback to fake provider (intentional: provider identity must be explicit)
- Source: `src/ticketpilot/drafting/provider.py`

**Remaining limitation**: Phase 12 had 0 API errors. Error handling has not been exercised under real network conditions.

**Next improvement**: Test with simulated API errors and network latency.

---

## 3. Engineering Quality Issues

### 3.1 Phase 12C.1 Quality Gate Weakening

**Symptom**: Integration test skip count was not enforced in the quality gate — the `TICKETPILOT_SKIP_DB_TESTS=1` guard was changed from FAIL to WARN, allowing the gate to pass with skipped tests.

**Likely root causes**:
- The quality gate was temporarily modified to speed up development iterations
- The modification was not reverted before committing comparison results

**System response**:
- Phase 12C.1 flagged the issue when attempting to restore strict gate
- Phase 12C.2 identified root cause: `.env.local` sets `TICKETPILOT_LLM_PROVIDER=openai_compatible`, causing tests to use the real provider
- Phase 12C.2 fix: added `export TICKETPILOT_LLM_PROVIDER=fake` before test runs in `scripts/run_quality_gate.sh`
- Quality gate fully restored: strict policy enforced (0 skipped), 1069 unit + 146 integration tests

**Remaining limitation**: This was an engineering QA issue, not a product feature. The fix ensures tests run in isolation from local real-provider configuration.

**Prevention**: No `|| true` bypass in quality gate; integration skipped must = 0 for archive/push per AGENTS.md.

---

### 3.2 WSL psycopg DLL Loading

**Symptom**: Integration tests were skipped in WSL environment due to psycopg DLL loading failure.

**Likely root causes**:
- WSL UNC path limitations prevent Windows psycopg from loading native DLLs
- Cross-filesystem SQLite coverage data corruption

**System response**:
- `conftest.py` and `connection.py` include DLL repair code
- Coverage file moved to `/tmp` to avoid cross-filesystem issues
- Phase 12C.2 quality gate ran successfully with 0 skipped (after DLL repair)

**Remaining limitation**: Requires WSL-specific repair code. Non-WSL environments (Linux, macOS) should not need this.

**Next improvement**: Document WSL-specific requirements in README.

---

## 4. Summary: Offline Evaluation Limitations

**Knowledge coverage remains a bottleneck.** The 9 genuine retrieval misses in Phase 10 include edge cases and domain-specific queries. Expanding the knowledge base would help, but adding synthetic knowledge is not equivalent to adding real coverage.

**Guardrails reduce risk but do not replace human review.** Claim guard and citation validation catch structural errors, but they do not verify that the draft text is factually correct, contextually appropriate, or free from subtle brand risk.

**Confidence is not correctness.** Fake provider confidence reflects evidence scores. Real provider confidence reflects model self-assessment. Neither is a reliable signal for auto-send decisions.

**The 25-case fixture set is not statistically significant.** Phase 12 comparison covers diverse scenarios but is not a representative sample. Conclusions should be limited to "the pipeline works on these cases" — not "the pipeline works generally."

**Phase 12 results are bounded by offline evaluation.** No live traffic, no real customer data, no production system. Results do not generalize.
