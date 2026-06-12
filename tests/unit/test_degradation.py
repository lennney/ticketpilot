"""Tests for DegradationRouter — tiered response strategy."""


from ticketpilot.confidence.scorer import ConfidenceBreakdown, ConfidenceLevel
from ticketpilot.degradation.router import (
    DEFAULT_DISCLAIMER,
    DegradationRouter,
    ResponseStrategy,
)


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
