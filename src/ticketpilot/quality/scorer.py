"""Draft quality scoring — determines if a draft is safe to auto-send.

Computes a quality score (0-1) from 4 dimensions:
- forbidden_promise: guardrail check result (binary, veto power)
- citation_precision: proportion of claims with valid citations (0-1)
- claim_guard: claim_guard_passed from drafting (binary)
- evidence_coverage: retrieved/expected evidence ratio (0-1)

Quality score determines routing:
- >= 0.7: eligible for auto-send
- >= 0.5: eligible for cautious auto-send (MEDIUM confidence)
- < 0.5: must go to human review
"""

from __future__ import annotations

from dataclasses import dataclass, field

# Thresholds
QUALITY_THRESHOLD_AUTO_SEND = 0.7
QUALITY_THRESHOLD_CAUTIOUS = 0.5


@dataclass
class QualityCheckResult:
    """Result of a single quality check."""

    name: str
    passed: bool
    score: float  # 0.0 to 1.0
    message: str = ""


@dataclass
class DraftQualityResult:
    """Aggregate quality assessment for a draft."""

    overall_score: float  # 0.0 to 1.0
    checks: list[QualityCheckResult] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    eligible_for_auto_send: bool = False
    eligible_for_cautious_send: bool = False
    vetoed: bool = False  # forbidden_promise triggered

    @property
    def passed(self) -> bool:
        return self.overall_score >= QUALITY_THRESHOLD_AUTO_SEND


def check_forbidden_promise(guardrail_passed: bool) -> QualityCheckResult:
    """Check if draft passed guardrails (forbidden promises, PII, etc.).
    This is a VETO check — failure sets score to 0."""
    return QualityCheckResult(
        name="forbidden_promise",
        passed=guardrail_passed,
        score=1.0 if guardrail_passed else 0.0,
        message=""
        if guardrail_passed
        else "Draft contains forbidden promises or guardrail violations",
    )


def check_citation_precision(citation_precision: float) -> QualityCheckResult:
    """Check citation quality.
    >= 0.8 = full score, >= 0.5 = partial, < 0.5 = fail."""
    if citation_precision >= 0.8:
        score = 1.0
    elif citation_precision >= 0.5:
        score = 0.5
    else:
        score = 0.0
    return QualityCheckResult(
        name="citation_precision",
        passed=citation_precision >= 0.5,
        score=score,
        message=f"Citation precision: {citation_precision:.0%}" if score < 1.0 else "",
    )


def check_claim_guard(claim_guard_passed: bool) -> QualityCheckResult:
    """Check if claim guard passed."""
    return QualityCheckResult(
        name="claim_guard",
        passed=claim_guard_passed,
        score=1.0 if claim_guard_passed else 0.0,
        message="" if claim_guard_passed else "Claim guard check failed",
    )


def check_evidence_coverage(evidence_coverage: float) -> QualityCheckResult:
    """Check evidence coverage.
    >= 0.7 = full, >= 0.4 = partial, < 0.4 = fail."""
    if evidence_coverage >= 0.7:
        score = 1.0
    elif evidence_coverage >= 0.4:
        score = 0.5
    else:
        score = 0.0
    return QualityCheckResult(
        name="evidence_coverage",
        passed=evidence_coverage >= 0.4,
        score=score,
        message=f"Evidence coverage: {evidence_coverage:.0%}" if score < 1.0 else "",
    )


def compute_draft_quality(
    guardrail_passed: bool,
    citation_precision: float = 1.0,
    claim_guard_passed: bool = True,
    evidence_coverage: float = 1.0,
) -> DraftQualityResult:
    """Compute overall draft quality from 4 dimensions.

    Args:
        guardrail_passed: Whether draft passed all guardrail checks.
        citation_precision: Ratio of valid citations (0-1).
        claim_guard_passed: Whether claim guard check passed.
        evidence_coverage: Ratio of retrieved/expected evidence (0-1).

    Returns:
        DraftQualityResult with overall score and eligibility flags.
    """
    checks = [
        check_forbidden_promise(guardrail_passed),
        check_citation_precision(citation_precision),
        check_claim_guard(claim_guard_passed),
        check_evidence_coverage(evidence_coverage),
    ]

    failures = [c.name for c in checks if not c.passed]
    vetoed = not guardrail_passed  # forbidden_promise has veto power

    if vetoed:
        overall_score = 0.0
    else:
        # Weighted average of non-veto checks
        weights = {
            "citation_precision": 0.35,
            "claim_guard": 0.30,
            "evidence_coverage": 0.35,
        }
        total_weight = 0.0
        weighted_sum = 0.0
        for check in checks:
            w = weights.get(check.name, 0)
            if w > 0:
                weighted_sum += check.score * w
                total_weight += w
        overall_score = weighted_sum / total_weight if total_weight > 0 else 0.0

    return DraftQualityResult(
        overall_score=round(overall_score, 3),
        checks=checks,
        failures=failures,
        eligible_for_auto_send=overall_score >= QUALITY_THRESHOLD_AUTO_SEND,
        eligible_for_cautious_send=overall_score >= QUALITY_THRESHOLD_CAUTIOUS,
        vetoed=vetoed,
    )
