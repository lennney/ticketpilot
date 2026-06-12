# Design: Guard Architecture — Granular Failure Taxonomy

## Before (Phase 13.10)

`GuardResult` uses simplified boolean fields:

```python
@dataclass
class GuardResult:
    citation_coverage: float
    has_uncited_claims: bool       # True → guard fails
    has_forbidden_promise: bool     # True → guard fails
    forbidden_promise_details: list[str]
    evidence_sufficiency: str       # "sufficient" | "partial" | "insufficient"
    risk_flags_respected: bool      # True → passes, False → guard fails
    guard_passed: bool             # AND of all checks
```

### Current Failure Distribution (Phase 13.10)

| Case | `has_uncited_claims` | `has_forbidden_promise` | `risk_flags_respected` | `guard_passed` |
|---|---|---|---|---|
| p12_011 | — | — | **False** | False |
| p12_015 | — | — | **False** | False |
| p12_018 | **True** | **True** | — | False |
| p12_021 | **True** or — | — | **False** | False |

All 4 failures collapse to `guard_passed=False` without revealing the specific failure mode.

---

## After (Phase 14+)

Extend `GuardResult` with a `failure_reasons: list[GuardFailureType]` field:

```python
class GuardFailureType(Enum):
    UNSUPPORTED_POLICY_CLAIM = "unsupported_policy_claim"
    FORBIDDEN_PROMISE = "forbidden_promise"
    MISSING_RISK_ESCALATION = "missing_risk_escalation"
    SAFE_ESCALATION_STATEMENT = "safe_escalation_statement"
    MANUAL_REVIEW_ACKNOWLEDGEMENT = "manual_review_acknowledgement"
    EVIDENCE_INSUFFICIENT_FALLBACK = "evidence_insufficient_fallback"
    AMBIGUOUS_GUARD_CASE = "ambiguous_guard_case"

@dataclass
class GuardResult:
    citation_coverage: float
    has_uncited_claims: bool
    has_forbidden_promise: bool
    forbidden_promise_details: list[str]
    evidence_sufficiency: str
    risk_flags_respected: bool
    guard_passed: bool
    # NEW: granular failure reasons
    failure_reasons: list[GuardFailureType]
```

### Taxonomy-to-Boolean Mapping (backward compatible)

| Boolean | Granular Type(s) |
|---|---|
| `has_uncited_claims=True` | `UNSUPPORTED_POLICY_CLAIM` |
| `has_forbidden_promise=True` | `FORBIDDEN_PROMISE` |
| `risk_flags_respected=False` | `MISSING_RISK_ESCALATION` |

### Failure Mapping: Phase 13.10 Cases

| Case | Current Failure | Proposed Taxonomy | Interpretation |
|---|---|---|---|
| p12_011 | `risk_flags_respected=False` | `MISSING_RISK_ESCALATION` | **Correct block.** Citations present but privacy risk flag (present in ticket) not acknowledged with escalation language. Guard correctly blocks. |
| p12_015 | `risk_flags_respected=False` | `MISSING_RISK_ESCALATION` | **Correct block.** Citations present but legal risk flag (present in ticket) not acknowledged with escalation language. Guard correctly blocks. |
| p12_018 | `has_uncited_claims=True` + `has_forbidden_promise=True` | `UNSUPPORTED_POLICY_CLAIM` + `FORBIDDEN_PROMISE` | **Correct block.** Draft makes 2 substantive claims without citations AND includes forbidden compensation amount. Guard correctly blocks. |
| p12_021 | Report: `has_uncited_claims=True`; Summary: `risk_flags_respected` | `UNCITED_SUBSTANTIVE_CLAIM` or `MISSING_RISK_ESCALATION` | **Ambiguous guard case.** Report text (draft without `[chunk_id]` citation markers) conflicts with summary JSON (reason=risk_flags_respected). Row-level data shows all fields as None. Requires manual recheck. |

### Key Design Decisions

1. **Additive only**: The taxonomy extends `GuardResult` without changing existing boolean fields. `guard_passed` logic is unchanged. Existing consumers are unaffected.

2. **`failure_reasons` is a list**: A draft can have multiple failure types (e.g., p12_018). A list allows reporting all failures simultaneously.

3. **`AMBIGUOUS_GUARD_CASE` as catch-all**: For cases where the available data cannot determine the failure type (e.g., p12_021 discrepancy between report and summary JSON). This surfaces the ambiguity rather than hiding it.

4. **Safe escalation and manual review are separate types**: Drafts may contain escalation language without being reviewer-ready. These are distinct signal types:
   - `SAFE_ESCALATION_STATEMENT`: Draft acknowledges escalation is needed
   - `MANUAL_REVIEW_ACKNOWLEDGEMENT`: Draft acknowledges human review requirement

5. **`MISSING_RISK_ESCALATION` is distinct from `UNSUPPORTED_POLICY_CLAIM`**: A draft can cite evidence (citations present) but still fail to acknowledge HIGH-severity risk flags. These require different interventions:
   - `UNSUPPORTED_POLICY_CLAIM`: Prompt improvement or evidence retrieval
   - `MISSING_RISK_ESCALATION`: Prompt improvement with stronger escalation language

6. **Evidence-insufficient fallback is a taxonomy type**: Safe fallback drafts (which lack citations) are currently flagged as `has_uncited_claims=True`. With taxonomy, they can be specifically typed as `EVIDENCE_INSUFFICIENT_FALLBACK`, distinguishing them from substantive drafts that fail to cite.

7. **No weakening of guard**: The taxonomy does not change whether a guard passes or fails. It only provides more granular classification of why it failed.
