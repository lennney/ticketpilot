"""Tests for the keyword trade-off analysis module."""

from __future__ import annotations

import pytest

from ticketpilot.evaluation.schemas import EvalTicket, GoldenExpectation
from ticketpilot.optimizer.diagnostics import Diagnosis, TYPE_INTENT_MISMATCH
from ticketpilot.optimizer.tradeoff import (
    KeywordTradeoff,
    _keyword_in_rule,
    _temporary_keyword,
    analyze_keyword_tradeoff,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ticket(case_id: str, text: str, scenario: str = "complaint") -> EvalTicket:
    return EvalTicket(
        case_id=case_id,
        original_text=text,
        submitted_at="2025-01-01",
        scenario_type=scenario,
    )


def _make_golden(case_id: str, issue_type: str) -> GoldenExpectation:
    return GoldenExpectation(
        case_id=case_id,
        expected_issue_type=issue_type,
        expected_severity="medium",
        expected_must_human_review=False,
        expected_fallback_required=False,
        expected_no_auto_send=True,
    )


def _make_diagnosis(affected_cases: list[str], intent: str) -> Diagnosis:
    return Diagnosis(
        type=TYPE_INTENT_MISMATCH,
        priority=2,
        affected_cases=affected_cases,
        expected_values={"intent": intent},
        predicted_values={"predicted_intent": "other"},
        suggested_fix_type="intent_keyword",
        suggested_keywords=[],
        fix_gain=0.1,
        description="Intent mismatch",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestKeywordTradeoff:
    """Tests for the analyze_keyword_tradeoff function."""

    def test_analyze_returns_net_gain_for_known_keyword(self):
        """Adding '发票' to refund should fix cluster cases and may harm outside cases."""
        # Use a keyword that is NOT already in any rule
        keyword = "发票"
        target_intent = "refund"
        assert not _keyword_in_rule(target_intent, keyword), (
            f"'{keyword}' should not already be in {target_intent} rule"
        )

        diagnosis = _make_diagnosis(
            affected_cases=["T001", "T002"],
            intent=target_intent,
        )

        # Cluster cases: currently classified as 'other', expected 'refund'
        tickets = {
            "T001": _make_ticket("T001", "开发票报销"),
            "T002": _make_ticket("T002", "开一张发票"),
            # Outside cases
            "T003": _make_ticket("T003", "发票已开好"),
            "T004": _make_ticket("T004", "包裹什么时候到"),
        }

        golden = {
            "T001": _make_golden("T001", "refund"),
            "T002": _make_golden("T002", "refund"),
            "T003": _make_golden("T003", "other"),
            "T004": _make_golden("T004", "logistics"),
        }

        result = analyze_keyword_tradeoff(diagnosis, keyword, tickets, golden)

        assert isinstance(result, KeywordTradeoff)
        assert result.keyword == keyword
        assert result.target_intent == target_intent
        # T001 and T002 should be fixed (发票 in text → refund matches golden)
        assert "T001" in result.fixed_case_ids
        assert "T002" in result.fixed_case_ids
        # T003 (发票已开好, golden=other) was correctly 'other', now becomes 'refund' → harmed
        assert "T003" in result.harmed_case_ids
        # T004 (包裹什么时候到, golden=logistics) remains 'logistics' → not harmed
        assert "T004" not in result.harmed_case_ids
        # net_gain = 2 fixed - 1 harmed = 1
        assert result.net_gain == 1
        assert result.is_positive

    def test_duplicate_keyword_returns_zero_net_gain(self):
        """Adding a keyword already in the rule should return net_gain=0."""
        keyword = "退款"
        target_intent = "refund"
        assert _keyword_in_rule(target_intent, keyword), (
            f"'{keyword}' should already be in {target_intent} rule"
        )

        diagnosis = _make_diagnosis(
            affected_cases=["T001"],
            intent=target_intent,
        )

        tickets = {
            "T001": _make_ticket("T001", "我要退款"),
        }
        golden = {
            "T001": _make_golden("T001", "refund"),
        }

        result = analyze_keyword_tradeoff(diagnosis, keyword, tickets, golden)

        assert result.net_gain == 0
        assert result.fixed_case_ids == []
        assert result.harmed_case_ids == []
        assert "Already in rule" in result.description

    def test_restores_original_rules_after_simulation(self):
        """INTENT_RULES should be unchanged after analyze_keyword_tradeoff."""
        from ticketpilot.classification.rules import INTENT_RULES

        # Snapshot original state
        original_keywords = {
            rule.intent.value: list(rule.keywords) for rule in INTENT_RULES
        }

        keyword = "发票"
        target_intent = "refund"
        assert not _keyword_in_rule(target_intent, keyword)

        diagnosis = _make_diagnosis(
            affected_cases=["T001"],
            intent=target_intent,
        )
        tickets = {
            "T001": _make_ticket("T001", "开发票报销"),
            "T002": _make_ticket("T002", "包裹什么时候到"),
        }
        golden = {
            "T001": _make_golden("T001", "refund"),
            "T002": _make_golden("T002", "logistics"),
        }

        analyze_keyword_tradeoff(diagnosis, keyword, tickets, golden)

        # Verify all rules are restored
        for rule in INTENT_RULES:
            assert rule.keywords == original_keywords[rule.intent.value], (
                f"Keywords for {rule.intent.value} were not restored"
            )

    def test_no_target_intent_returns_zero_net_gain(self):
        """Empty expected_values should return net_gain=0 with appropriate description."""
        diagnosis = Diagnosis(
            type=TYPE_INTENT_MISMATCH,
            priority=2,
            affected_cases=["T001"],
            expected_values={},  # No "intent" key
            predicted_values={"predicted_intent": "other"},
            suggested_fix_type="intent_keyword",
            suggested_keywords=[],
            fix_gain=0.1,
            description="Intent mismatch",
        )

        result = analyze_keyword_tradeoff(
            diagnosis,
            "发票",
            {},
            {},
        )

        assert result.net_gain == 0
        assert result.fixed_case_ids == []
        assert result.harmed_case_ids == []
        assert "No target intent" in result.description

    def test_keyword_tradeoff_is_positive_property(self):
        """KeywordTradeoff.is_positive should return True only when net_gain > 0."""
        # Positive
        p = KeywordTradeoff(
            keyword="test",
            target_intent="refund",
            fixed_case_ids=["T001"],
            harmed_case_ids=[],
            net_gain=1,
            description="positive",
        )
        assert p.is_positive

        # Zero
        z = KeywordTradeoff(
            keyword="test",
            target_intent="refund",
            fixed_case_ids=[],
            harmed_case_ids=[],
            net_gain=0,
            description="zero",
        )
        assert not z.is_positive

        # Negative
        n = KeywordTradeoff(
            keyword="test",
            target_intent="refund",
            fixed_case_ids=[],
            harmed_case_ids=["T001"],
            net_gain=-1,
            description="negative",
        )
        assert not n.is_positive

    def test_temporary_keyword_restores_on_exception(self):
        """Even if code inside _temporary_keyword raises, rules should be restored."""
        from ticketpilot.classification.rules import INTENT_RULES

        # Snap original keywords for refund rule
        refund_rule = None
        for rule in INTENT_RULES:
            if rule.intent.value == "refund":
                refund_rule = rule
                break
        assert refund_rule is not None
        original_keywords = list(refund_rule.keywords)

        class _TestError(Exception):
            pass

        with pytest.raises(_TestError):
            with _temporary_keyword("refund", "__test_marker__"):
                refund_rule.keywords.append("should_be_restored")
                raise _TestError("simulated failure")

        # Verify rule is restored despite the exception
        assert refund_rule.keywords == original_keywords
        assert "__test_marker__" not in refund_rule.keywords
        assert "should_be_restored" not in refund_rule.keywords

    def test_current_predictions_used_outside_cluster(self):
        """When current_predictions is provided, outside cases should use cached values."""
        keyword = "发票"
        target_intent = "refund"
        assert not _keyword_in_rule(target_intent, keyword)

        diagnosis = _make_diagnosis(
            affected_cases=["T001", "T002"],
            intent=target_intent,
        )

        tickets = {
            "T001": _make_ticket("T001", "开发票报销"),
            "T002": _make_ticket("T002", "开一张发票"),
            "T003": _make_ticket("T003", "发票已开好"),
            "T004": _make_ticket("T004", "包裹什么时候到"),
        }
        golden = {
            "T001": _make_golden("T001", "refund"),
            "T002": _make_golden("T002", "refund"),
            "T003": _make_golden("T003", "other"),
            "T004": _make_golden("T004", "logistics"),
        }

        # Provide cached predictions
        current_predictions = {
            "T003": "other",  # correct cache
            "T004": "logistics",  # correct cache
        }

        result = analyze_keyword_tradeoff(
            diagnosis,
            keyword,
            tickets,
            golden,
            current_predictions=current_predictions,
        )

        # Should work correctly with cached predictions
        assert "T001" in result.fixed_case_ids
        assert "T002" in result.fixed_case_ids
        assert "T003" in result.harmed_case_ids
        assert "T004" not in result.harmed_case_ids
        assert result.net_gain == 1
