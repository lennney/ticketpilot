# TicketPilot Documentation Inventory

**Generated:** 2026-05-02
**Purpose:** Pre-Batch 1 documentation hygiene — assess existing docs for staleness,
contradictions with current implementation, and required actions before creating
development_trace / technical / skills documentation in later batches.

---

## 1. Inventory Table

| # | Document | Status | Conflict Risk | Recommended Action | Action Taken | Replacement / Redirect | Reusable Content |
|---|----------|--------|---------------|-------------------|-------------|----------------------|-----------------|
| 1 | `docs/architecture.md` | KEEP_WITH_NOTE | LOW | Add status note clarifying implemented vs. planned stages | Note added at top of file | `docs/technical_decisions.md`, `docs/phase_status.md` | Workflow description is directionally correct for most stages |
| 2 | `docs/retrieval_design.md` | DEPRECATE_AND_REDIRECT | HIGH | Add prominent deprecation banner; redirect to `technical_decisions.md` | Deprecation header added with specific mismatches listed | `docs/technical_decisions.md` | Architecture overview and rationale sections are still useful context (embedding tier strategy, RRF algorithm description, risk analysis) |
| 3 | `docs/retrieval_spec.md` | DEPRECATE_AND_REDIRECT | MEDIUM | Add deprecation banner noting it was never promoted to official OpenSpec; redirect to archived changes | Deprecation header added with redirect | `docs/technical_decisions.md`, `openspec/changes/archive/` | Functional requirements (FR-1 through FR-8) are directionally valid as high-level goals |
| 4 | `docs/ai_development_workflow.md` | KEEP_CURRENT | NONE | No changes needed — process document describing the development workflow still in use | None (kept as-is) | N/A | Full content — describes the spec-driven development process currently used |
| 5 | `docs/qa_evaluation_batch1.md` | MOVE_TO_LEGACY | LOW | Move to `docs/legacy/` — historical QA report for an archived change | Moved to `docs/legacy/qa_evaluation_batch1.md` | N/A (historical record only) | Golden case definitions (GC1-GC8) and risk flag test scenarios are referenceable for future regression testing |
| 6 | `docs/evaluation_plan.md` | KEEP_WITH_NOTE | LOW | Add note clarifying that evaluation scripts are not yet implemented | Note added at top of file | `docs/phase_status.md` | 5-layer evaluation taxonomy is a useful framework reference |

---

## 2. Additional Notable Documents

| Document | Status | Notes |
|----------|--------|-------|
| `docs/changelog.md` | ACTIVE | Maintained per-entry; reflects all implemented changes. |
| `docs/phase_status.md` | ACTIVE | Maintained per-stage; reflects current acceptance status. |
| `docs/technical_decisions.md` | ACTIVE | Maintained as authoritative implementation reference. Updated during audit remediation. |
| `docs/demo_cases.md` | KEEP_CURRENT | Brief list of 8 demo scenarios matching golden cases. No contradictions. |
| `docs/audits/project_plan_audit_2026-04-29.md` | KEEP_CURRENT | Historical audit report. All blocking issues resolved. |
| `docs/legacy/README.md` | NEW | Created to document legacy directory policy. |
| `docs/legacy/qa_evaluation_batch1.md` | LEGACY | Moved from `docs/qa_evaluation_batch1.md`. |
| `docs/documentation_inventory.md` | NEW | This file — created as the main deliverable of Pre-Batch 1 hygiene. |

---

## 3. Detailed Assessment

### 3.1 docs/architecture.md

**Why kept:** The document is a 21-line high-level workflow description. Most stages
(ticket input through human review) are now implemented. Only `rerank`, `finalization`,
and `trace write-back` remain as future work. The document is directionally correct
and provides useful context for new readers.

**Note added:** Clarifies which stages are implemented vs. planned and points to
`docs/technical_decisions.md` and `docs/phase_status.md`.

**Conflict risk:** LOW — the workflow described is aspirational but not contradictory.
No specific implementation claims are made.

### 3.2 docs/retrieval_design.md

**Why deprecated:** Contains numerous specific values that contradict current implementation:
- Fake embedding dimension: doc says 128, code uses **384**
- FTS config: doc says `chinese`, code uses **`simple`**
- HNSW ef_construction: doc says 64, code uses **200**
- Table schema: doc primarily describes single-table design, code uses **`knowledge_chunks` + 3 source tables**
- SourceRouter: documented as implemented, actually **deferred**

**Action:** Prominent deprecation banner added at the top listing each specific mismatch,
with redirect to `docs/technical_decisions.md` (Retrieval Architecture section).

**Conflict risk:** HIGH — specific numeric and config claims directly contradict
implementation. Banner resolves this by clearly marking the document as inaccurate.

**Reusable content:** The embedding tier strategy rationale, RRF algorithm description,
and risk analysis sections provide architectural context that is still valid at the
design-intent level.

### 3.3 docs/retrieval_spec.md

**Why deprecated:** This document was created during early design and was never promoted
to an OpenSpec spec. The authoritative specs live in `openspec/specs/`. Specific values
(embedding dimensions 128/3072) do not match implementation (384).

**Action:** Deprecation header added with redirect to `docs/technical_decisions.md`
and archived OpenSpec changes.

**Conflict risk:** MEDIUM — contains aspirational parameter values that differ from
implementation but does not claim to reflect current state.

### 3.4 docs/ai_development_workflow.md

**Why kept:** This document describes the 4-layer development workflow (Planning Brain,
Implementation Body, Supervision, Quality Gate) that is still actively used. No
contradictions with current practice.

**Conflict risk:** NONE.

### 3.5 docs/qa_evaluation_batch1.md

**Why moved:** This is a historical QA report for an archived batch change (Batch 1 of
the ticket intake pipeline). It is 15 KB, contains detailed golden case definitions,
but was written for a specific past acceptance review. Keeping it in the active docs
directory creates confusion about whether it reflects current project state.

**Action:** Moved to `docs/legacy/qa_evaluation_batch1.md`. The legacy directory
README documents the preservation policy.

**Reusable content:** Golden case definitions (GC1-GC8), risk flag test scenarios, and
the structured acceptance report format are referenceable for future regression testing.

### 3.6 docs/evaluation_plan.md

**Why kept:** The 5-layer evaluation taxonomy (classification, retrieval, evidence,
risk gate, human review) is a useful framework reference. No specific implementation
claims are made — it is aspirational by design.

**Note added:** Clarifies that evaluation scripts are not yet implemented and points
to `docs/phase_status.md` for current state.

**Conflict risk:** LOW.

---

## 4. Summary

| Outcome | Count | Documents |
|---------|-------|-----------|
| KEEP_CURRENT | 2 | `ai_development_workflow.md`, `demo_cases.md` |
| KEEP_WITH_NOTE | 2 | `architecture.md`, `evaluation_plan.md` |
| DEPRECATE_AND_REDIRECT | 2 | `retrieval_design.md`, `retrieval_spec.md` |
| MOVE_TO_LEGACY | 1 | `qa_evaluation_batch1.md` |
| DELETE | 0 | — |

**Remaining contradictions:** None. Every document with outdated claims has been
annotated, deprecated, or moved. Documents kept without modification (`ai_development_workflow.md`,
`demo_cases.md`) contain no claims that contradict current implementation.
