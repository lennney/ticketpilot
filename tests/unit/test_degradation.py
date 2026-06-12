"""Tests for DegradationRouter — tiered response strategy."""


from ticketpilot.confidence.scorer import ConfidenceBreakdown, ConfidenceLevel
from ticketpilot.degradation.router import (
    DEFAULT_DISCLAIMER,
    DegradationRouter,
    ResponseStrategy,
)
from ticketpilot.quality.scorer import DraftQualityResult


class TestDegradationRouter:
    """Tests for DegradationRouter.route()."""

    def _make_confidence(self, overall: float, level: ConfidenceLevel) -> ConfidenceBreakdown:
        """Helper to create ConfidenceBreakdown."""
        return ConfidenceBreakdown(
            retrieval_confidence=overall,
            classification_confidence=overall,
            citation_confidence=overall,
            evidence_density=overall,
            overall=overall,
            level=level,
        )

    def test_high_confidence_auto_send(self):
        """HIGH confidence → AUTO_SEND, no disclaimer."""
        router = DegradationRouter()
        conf = self._make_confidence(0.9, ConfidenceLevel.HIGH)
        result = router.route(conf, draft="测试回复")

        assert result.strategy == ResponseStrategy.AUTO_SEND
        assert result.answer == "测试回复"
        assert result.disclaimer is None
        assert result.escalation_reason is None
        assert result.human_handoff_context is None

    def test_medium_confidence_auto_send_cautious(self):
        """MEDIUM confidence → AUTO_SEND_CAUTIOUS with disclaimer."""
        router = DegradationRouter()
        conf = self._make_confidence(0.7, ConfidenceLevel.MEDIUM)
        result = router.route(conf, draft="测试回复")

        assert result.strategy == ResponseStrategy.AUTO_SEND_CAUTIOUS
        assert result.answer == "测试回复"
        assert result.disclaimer == DEFAULT_DISCLAIMER
        assert result.escalation_reason is None

    def test_low_confidence_human_review(self):
        """LOW confidence → HUMAN_REVIEW with escalation reason."""
        router = DegradationRouter()
        conf = self._make_confidence(0.5, ConfidenceLevel.LOW)
        result = router.route(conf, draft="测试回复")

        assert result.strategy == ResponseStrategy.HUMAN_REVIEW
        assert result.answer == "测试回复"
        assert result.escalation_reason is not None
        assert "低置信度" in result.escalation_reason

    def test_critical_confidence_escalation(self):
        """CRITICAL confidence → HUMAN_ESCALATION, no answer, handoff context."""
        router = DegradationRouter()
        conf = self._make_confidence(0.2, ConfidenceLevel.CRITICAL)
        result = router.route(conf, draft="测试回复")

        assert result.strategy == ResponseStrategy.HUMAN_ESCALATION
        assert result.answer is None  # No draft for critical
        assert result.escalation_reason is not None
        assert "极低置信度" in result.escalation_reason
        assert result.human_handoff_context is not None
        assert result.human_handoff_context["reason"] == "critical_confidence"
        assert result.human_handoff_context["attempted_draft"] == "测试回复"

    def test_critical_without_draft(self):
        """CRITICAL without draft still works."""
        router = DegradationRouter()
        conf = self._make_confidence(0.1, ConfidenceLevel.CRITICAL)
        result = router.route(conf)

        assert result.strategy == ResponseStrategy.HUMAN_ESCALATION
        assert result.answer is None
        assert result.human_handoff_context["attempted_draft"] is None

    def test_all_strategies_covered(self):
        """All 4 confidence levels map to different strategies."""
        router = DegradationRouter()
        strategies = set()

        for level, overall in [
            (ConfidenceLevel.HIGH, 0.9),
            (ConfidenceLevel.MEDIUM, 0.7),
            (ConfidenceLevel.LOW, 0.5),
            (ConfidenceLevel.CRITICAL, 0.2),
        ]:
            conf = self._make_confidence(overall, level)
            result = router.route(conf, draft="test")
            strategies.add(result.strategy)

        assert len(strategies) == 4
        assert strategies == {
            ResponseStrategy.AUTO_SEND,
            ResponseStrategy.AUTO_SEND_CAUTIOUS,
            ResponseStrategy.HUMAN_REVIEW,
            ResponseStrategy.HUMAN_ESCALATION,
        }


class TestQualityGateRouting:
    """Tests for quality gate integration in DegradationRouter."""

    def _make_confidence(self, overall: float, level: ConfidenceLevel) -> ConfidenceBreakdown:
        """Helper to create ConfidenceBreakdown."""
        return ConfidenceBreakdown(
            retrieval_confidence=overall,
            classification_confidence=overall,
            citation_confidence=overall,
            evidence_density=overall,
            overall=overall,
            level=level,
        )

    def _make_quality(self, eligible_for_auto: bool = True, eligible_for_cautious: bool = True) -> DraftQualityResult:
        """Helper to create DraftQualityResult."""
        return DraftQualityResult(
            overall_score=0.9 if eligible_for_auto else 0.3,
            eligible_for_auto_send=eligible_for_auto,
            eligible_for_cautious_send=eligible_for_cautious,
            failures=[] if eligible_for_auto else ["unsupported_claims"],
        )
    def test_high_confidence_good_quality(self):
        """HIGH confidence + good quality → AUTO_SEND."""
        router = DegradationRouter()
        conf = self._make_confidence(0.9, ConfidenceLevel.HIGH)
        quality = self._make_quality(eligible_for_auto=True)
        result = router.route(conf, draft="测试回复", quality=quality)

        assert result.strategy == ResponseStrategy.AUTO_SEND
        assert result.answer == "测试回复"
        assert result.quality is not None
        assert result.quality.eligible_for_auto_send is True
        assert result.escalation_reason is None

    def test_high_confidence_bad_quality(self):
        """HIGH confidence + bad quality → HUMAN_REVIEW."""
        router = DegradationRouter()
        conf = self._make_confidence(0.9, ConfidenceLevel.HIGH)
        quality = self._make_quality(eligible_for_auto=False)
        result = router.route(conf, draft="测试回复", quality=quality)

        assert result.strategy == ResponseStrategy.HUMAN_REVIEW
        assert result.answer == "测试回复"
        assert result.quality is not None
        assert result.quality.eligible_for_auto_send is False
        assert result.escalation_reason is not None
        assert "草稿质量不足" in result.escalation_reason

    def test_medium_confidence_good_quality(self):
        """MEDIUM confidence + good quality → AUTO_SEND_CAUTIOUS."""
        router = DegradationRouter()
        conf = self._make_confidence(0.7, ConfidenceLevel.MEDIUM)
        quality = self._make_quality(eligible_for_cautious=True)
        result = router.route(conf, draft="测试回复", quality=quality)

        assert result.strategy == ResponseStrategy.AUTO_SEND_CAUTIOUS
        assert result.answer == "测试回复"
        assert result.quality is not None
        assert result.quality.eligible_for_cautious_send is True
        assert result.disclaimer == DEFAULT_DISCLAIMER

    def test_medium_confidence_bad_quality(self):
        """MEDIUM confidence + bad quality → HUMAN_REVIEW."""
        router = DegradationRouter()
        conf = self._make_confidence(0.7, ConfidenceLevel.MEDIUM)
        quality = self._make_quality(eligible_for_cautious=False)
        result = router.route(conf, draft="测试回复", quality=quality)

        assert result.strategy == ResponseStrategy.HUMAN_REVIEW
        assert result.answer == "测试回复"
        assert result.quality is not None
        assert result.quality.eligible_for_cautious_send is False
        assert result.escalation_reason is not None
        assert "草稿质量不足" in result.escalation_reason

    def test_quality_none_backward_compat(self):
        """quality=None → same behavior as before (no quality gate)."""
        router = DegradationRouter()

        # HIGH confidence, no quality → AUTO_SEND
        conf_high = self._make_confidence(0.9, ConfidenceLevel.HIGH)
        result_high = router.route(conf_high, draft="测试回复")
        assert result_high.strategy == ResponseStrategy.AUTO_SEND
        assert result_high.quality is None

        # MEDIUM confidence, no quality → AUTO_SEND_CAUTIOUS
        conf_med = self._make_confidence(0.7, ConfidenceLevel.MEDIUM)
        result_med = router.route(conf_med, draft="测试回复")
        assert result_med.strategy == ResponseStrategy.AUTO_SEND_CAUTIOUS
        assert result_med.quality is None

    def test_forbidden_promise_veto(self):
        """Quality with forbidden promise failure → HUMAN_REVIEW regardless of confidence."""
        router = DegradationRouter()
        conf = self._make_confidence(0.9, ConfidenceLevel.HIGH)
        quality = DraftQualityResult(
            overall_score=0.0,
            eligible_for_auto_send=False,
            eligible_for_cautious_send=False,
            failures=["forbidden_promise"],
            vetoed=True,
        )
        result = router.route(conf, draft="我们保证解决您的问题", quality=quality)
        assert result.strategy == ResponseStrategy.HUMAN_REVIEW
        assert result.quality is not None
        assert result.quality.failures == ["forbidden_promise"]
        assert result.escalation_reason is not None

    def test_critical_always_escalates_regardless_of_quality(self):
        """CRITICAL confidence always escalates, even with perfect quality."""
        router = DegradationRouter()
        conf = self._make_confidence(0.2, ConfidenceLevel.CRITICAL)
        quality = self._make_quality(eligible_for_auto=True)
        result = router.route(conf, draft="测试回复", quality=quality)

        assert result.strategy == ResponseStrategy.HUMAN_ESCALATION
        assert result.answer is None
        assert result.human_handoff_context is not None
