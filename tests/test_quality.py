"""Tests for DraftQualityScorer — draft quality scoring module."""

from ticketpilot.quality.scorer import (
    QUALITY_THRESHOLD_AUTO_SEND,
    QUALITY_THRESHOLD_CAUTIOUS,
    DraftQualityResult,
    check_citation_precision,
    check_claim_guard,
    check_evidence_coverage,
    check_forbidden_promise,
    compute_draft_quality,
)


class TestCheckForbiddenPromise:
    def test_passed(self):
        result = check_forbidden_promise(True)
        assert result.passed is True
        assert result.score == 1.0
        assert result.name == "forbidden_promise"
        assert result.message == ""

    def test_failed(self):
        result = check_forbidden_promise(False)
        assert result.passed is False
        assert result.score == 0.0
        assert "forbidden" in result.message.lower()


class TestCheckCitationPrecision:
    def test_high_precision(self):
        result = check_citation_precision(0.9)
        assert result.passed is True
        assert result.score == 1.0

    def test_boundary_0_8(self):
        result = check_citation_precision(0.8)
        assert result.score == 1.0

    def test_medium_precision(self):
        result = check_citation_precision(0.6)
        assert result.passed is True
        assert result.score == 0.5

    def test_boundary_0_5(self):
        result = check_citation_precision(0.5)
        assert result.passed is True
        assert result.score == 0.5

    def test_low_precision(self):
        result = check_citation_precision(0.3)
        assert result.passed is False
        assert result.score == 0.0

    def test_zero_precision(self):
        result = check_citation_precision(0.0)
        assert result.passed is False
        assert result.score == 0.0


class TestCheckClaimGuard:
    def test_passed(self):
        result = check_claim_guard(True)
        assert result.passed is True
        assert result.score == 1.0
        assert result.name == "claim_guard"

    def test_failed(self):
        result = check_claim_guard(False)
        assert result.passed is False
        assert result.score == 0.0
        assert "claim guard" in result.message.lower()


class TestCheckEvidenceCoverage:
    def test_high_coverage(self):
        result = check_evidence_coverage(0.9)
        assert result.passed is True
        assert result.score == 1.0

    def test_boundary_0_7(self):
        result = check_evidence_coverage(0.7)
        assert result.score == 1.0

    def test_medium_coverage(self):
        result = check_evidence_coverage(0.5)
        assert result.passed is True
        assert result.score == 0.5

    def test_boundary_0_4(self):
        result = check_evidence_coverage(0.4)
        assert result.passed is True
        assert result.score == 0.5

    def test_low_coverage(self):
        result = check_evidence_coverage(0.2)
        assert result.passed is False
        assert result.score == 0.0

    def test_zero_coverage(self):
        result = check_evidence_coverage(0.0)
        assert result.passed is False
        assert result.score == 0.0


class TestComputeDraftQuality:
    def test_all_passing(self):
        """All checks pass → score >= 0.7, eligible_for_auto_send=True."""
        result = compute_draft_quality(
            guardrail_passed=True,
            citation_precision=1.0,
            claim_guard_passed=True,
            evidence_coverage=1.0,
        )
        assert isinstance(result, DraftQualityResult)
        assert result.overall_score >= QUALITY_THRESHOLD_AUTO_SEND
        assert result.eligible_for_auto_send is True
        assert result.eligible_for_cautious_send is True
        assert result.vetoed is False
        assert result.failures == []

    def test_forbidden_promise_veto(self):
        """Guardrail failed → score=0, vetoed=True."""
        result = compute_draft_quality(
            guardrail_passed=False,
            citation_precision=1.0,
            claim_guard_passed=True,
            evidence_coverage=1.0,
        )
        assert result.overall_score == 0.0
        assert result.vetoed is True
        assert result.eligible_for_auto_send is False
        assert result.eligible_for_cautious_send is False
        assert "forbidden_promise" in result.failures

    def test_low_citation(self):
        """Citation precision=0.3 → score < 0.7."""
        result = compute_draft_quality(
            guardrail_passed=True,
            citation_precision=0.3,
            claim_guard_passed=True,
            evidence_coverage=1.0,
        )
        # citation_precision=0.3 → score=0.0 for that check
        # weighted: 0.35*0.0 + 0.30*1.0 + 0.35*1.0 = 0.65 → below 0.7
        assert result.overall_score < QUALITY_THRESHOLD_AUTO_SEND
        assert result.vetoed is False
        assert "citation_precision" in result.failures

    def test_claim_guard_failed(self):
        """Claim guard failed → score reduced."""
        result = compute_draft_quality(
            guardrail_passed=True,
            citation_precision=1.0,
            claim_guard_passed=False,
            evidence_coverage=1.0,
        )
        # weighted: 0.35*1.0 + 0.30*0.0 + 0.35*1.0 = 0.70 → exactly at threshold
        assert result.overall_score == QUALITY_THRESHOLD_AUTO_SEND
        assert result.eligible_for_auto_send is True
        assert "claim_guard" in result.failures

    def test_low_evidence(self):
        """Evidence coverage=0.2 → score < 0.5."""
        result = compute_draft_quality(
            guardrail_passed=True,
            citation_precision=0.5,
            claim_guard_passed=True,
            evidence_coverage=0.2,
        )
        # citation_precision=0.5 → score=0.5, evidence_coverage=0.2 → score=0.0
        # weighted: 0.35*0.5 + 0.30*1.0 + 0.35*0.0 = 0.475
        assert result.overall_score < QUALITY_THRESHOLD_CAUTIOUS
        assert result.vetoed is False
        assert result.eligible_for_auto_send is False
        assert result.eligible_for_cautious_send is False

    def test_mixed_scores(self):
        """Some pass some fail → intermediate score."""
        result = compute_draft_quality(
            guardrail_passed=True,
            citation_precision=0.6,  # partial → score=0.5
            claim_guard_passed=True,
            evidence_coverage=0.5,  # partial → score=0.5
        )
        # weighted: 0.35*0.5 + 0.30*1.0 + 0.35*0.5 = 0.65
        assert 0.5 <= result.overall_score < 0.7
        assert result.vetoed is False
        assert result.eligible_for_cautious_send is True
        assert result.eligible_for_auto_send is False

    def test_cautious_eligible(self):
        """Score 0.5-0.7 → eligible_for_cautious_send=True."""
        # citation=0.5 (score=0.5), claim_guard=True (score=1.0), evidence=0.5 (score=0.5)
        result = compute_draft_quality(
            guardrail_passed=True,
            citation_precision=0.5,
            claim_guard_passed=True,
            evidence_coverage=0.5,
        )
        # weighted: 0.35*0.5 + 0.30*1.0 + 0.35*0.5 = 0.65
        assert result.overall_score >= QUALITY_THRESHOLD_CAUTIOUS
        assert result.overall_score < QUALITY_THRESHOLD_AUTO_SEND
        assert result.eligible_for_cautious_send is True
        assert result.eligible_for_auto_send is False

    def test_empty_evidence_full_score(self):
        """Evidence coverage=1.0, citation=1.0 → full score."""
        result = compute_draft_quality(
            guardrail_passed=True,
            citation_precision=1.0,
            claim_guard_passed=True,
            evidence_coverage=1.0,
        )
        assert result.overall_score == 1.0
        assert result.eligible_for_auto_send is True
        assert len(result.checks) == 4

    def test_checks_count(self):
        """Always 4 checks."""
        result = compute_draft_quality(guardrail_passed=True)
        assert len(result.checks) == 4
        names = {c.name for c in result.checks}
        assert names == {
            "forbidden_promise",
            "citation_precision",
            "claim_guard",
            "evidence_coverage",
        }

    def test_passed_property(self):
        """passed property reflects auto-send eligibility."""
        r1 = compute_draft_quality(guardrail_passed=True, evidence_coverage=1.0)
        assert r1.passed is True

        r2 = compute_draft_quality(guardrail_passed=True, evidence_coverage=0.0)
        assert r2.passed is False
