"""Unit tests for run_agent_pipeline (Batch 3).

All tests use mocked ToolRegistry — no real DB, LLM, or pipeline calls.
"""

from datetime import datetime

import pytest

from ticketpilot.agent.loop import run_agent_pipeline
from ticketpilot.agent.planner import DeterministicTaskPlanner
from ticketpilot.agent.registry import RegisteredTool, ToolRegistry
from ticketpilot.agent.schemas import (
    AgentEventType,
    AgentRunStatus,
    AgentToolSpec,
)
from ticketpilot.schema.ticket import RawTicket


# ---------------------------------------------------------------------------
# Mock registry helpers
# ---------------------------------------------------------------------------


def _make_constant_handler(result: dict):
    """Return a handler that always returns *result*."""

    def handler(data: dict) -> dict:
        return result

    return handler


def _make_fail_handler(msg: str = "mock error"):
    """Return a handler that raises RuntimeError."""

    def handler(data: dict) -> dict:
        raise RuntimeError(msg)

    return handler


def _make_mock_tool(name: str, handler, risk: str = "low") -> RegisteredTool:
    spec = AgentToolSpec(name=name, description=name, risk_level=risk)
    return RegisteredTool(spec=spec, handler=handler)


_NORMALIZED = {
    "text": "normalized text",
    "language": "zh",
    "order_numbers": [],
    "product_info": None,
    "amount": None,
    "cleaned_at": "2026-01-01T00:00:00",
}

_CLASSIFIED = {
    "intent": "refund",
    "confidence": 0.9,
    "classified_at": "2026-01-01T00:00:00",
}

_RISK_LOW = {
    "flags": [],
    "severity": "low",
    "must_human_review": False,
    "assessed_at": "2026-01-01T00:00:00",
}

_RISK_HIGH = {
    "flags": ["complaint_risk"],
    "severity": "high",
    "must_human_review": True,
    "assessed_at": "2026-01-01T00:00:00",
}

_EVIDENCE = {
    "evidence_candidates": [],
    "retrieval_trace": {"query": "test", "top_k": 10},
    "evidence_count": 0,
}

_DRAFT_OK = {
    "ticket_id": "mock",
    "draft_text": "mock reply",
    "citations": [],
    "evidence_used": [],
    "unsupported_claims": [],
    "missing_information": [],
    "confidence": 0.8,
    "must_human_review": False,
}

_DRAFT_REVIEW = {
    "ticket_id": "mock",
    "draft_text": "mock reply",
    "citations": [],
    "evidence_used": [],
    "unsupported_claims": ["low confidence"],
    "missing_information": [],
    "confidence": 0.3,
    "must_human_review": True,
}


def make_mock_registry(
    *,
    risk_assessment: dict | None = None,
    draft_reply: dict | None = None,
    fail_tool: str | None = None,
) -> ToolRegistry:
    """Create a ToolRegistry with mock handlers for all 5 tools.

    Args:
        risk_assessment: Override the risk assessment mock result.
        draft_reply: Override the draft reply mock result.
        fail_tool: Name of a tool that should raise RuntimeError.
    """
    risk = risk_assessment if risk_assessment is not None else _RISK_LOW
    draft = draft_reply if draft_reply is not None else _DRAFT_OK

    def _handler_for(name: str):
        if name == fail_tool:
            return _make_fail_handler(f"{name} failed")
        return _make_constant_handler(
            {
                "normalize_ticket": _NORMALIZED,
                "classify_ticket": _CLASSIFIED,
                "assess_risk": risk,
                "retrieve_evidence": _EVIDENCE,
                "generate_draft": draft,
            }[name]
        )

    registry = ToolRegistry()
    for name in (
        "normalize_ticket",
        "classify_ticket",
        "assess_risk",
        "retrieve_evidence",
        "generate_draft",
    ):
        registry.register(_make_mock_tool(name, _handler_for(name)))
    return registry


@pytest.fixture
def raw_ticket() -> RawTicket:
    return RawTicket(original_text="我要退款", submitted_at=datetime(2026, 1, 1))


# ---------------------------------------------------------------------------
# Basic run
# ---------------------------------------------------------------------------


class TestBasicRun:
    def test_returns_agent_run(self, raw_ticket):
        run = run_agent_pipeline(raw_ticket, registry=make_mock_registry())
        assert run.run_id is not None

    def test_final_status_completed(self, raw_ticket):
        run = run_agent_pipeline(raw_ticket, registry=make_mock_registry())
        assert run.final_status == AgentRunStatus.COMPLETED

    def test_plan_is_attached(self, raw_ticket):
        run = run_agent_pipeline(raw_ticket, registry=make_mock_registry())
        assert run.plan is not None
        assert len(run.plan.steps) == 5

    def test_ticket_output_is_attached(self, raw_ticket):
        run = run_agent_pipeline(raw_ticket, registry=make_mock_registry())
        assert run.ticket_output is not None
        assert run.ticket_output["ticket_id"] == run.run_id

    def test_draft_reply_is_attached(self, raw_ticket):
        run = run_agent_pipeline(raw_ticket, registry=make_mock_registry())
        assert run.draft_reply is not None
        assert run.draft_reply["draft_text"] == "mock reply"

    def test_review_decision_none(self, raw_ticket):
        run = run_agent_pipeline(raw_ticket, registry=make_mock_registry())
        assert run.review_decision is None

    def test_skill_id_none(self, raw_ticket):
        run = run_agent_pipeline(raw_ticket, registry=make_mock_registry())
        assert run.skill_id is None


# ---------------------------------------------------------------------------
# Event ordering
# ---------------------------------------------------------------------------


class TestEventOrdering:
    def test_events_include_run_started(self, raw_ticket):
        run = run_agent_pipeline(raw_ticket, registry=make_mock_registry())
        types = [e.event_type for e in run.events]
        assert AgentEventType.RUN_STARTED in types

    def test_events_include_plan_created(self, raw_ticket):
        run = run_agent_pipeline(raw_ticket, registry=make_mock_registry())
        types = [e.event_type for e in run.events]
        assert AgentEventType.PLAN_CREATED in types

    def test_events_include_tool_called_and_returned(self, raw_ticket):
        run = run_agent_pipeline(raw_ticket, registry=make_mock_registry())
        types = [e.event_type for e in run.events]
        assert AgentEventType.TOOL_CALLED in types
        assert AgentEventType.TOOL_RETURNED in types

    def test_events_include_draft_generated(self, raw_ticket):
        run = run_agent_pipeline(raw_ticket, registry=make_mock_registry())
        types = [e.event_type for e in run.events]
        assert AgentEventType.DRAFT_GENERATED in types

    def test_events_include_risk_checked(self, raw_ticket):
        run = run_agent_pipeline(raw_ticket, registry=make_mock_registry())
        types = [e.event_type for e in run.events]
        assert AgentEventType.RISK_CHECKED in types

    def test_events_include_run_completed(self, raw_ticket):
        run = run_agent_pipeline(raw_ticket, registry=make_mock_registry())
        types = [e.event_type for e in run.events]
        assert AgentEventType.RUN_COMPLETED in types

    def test_event_ordering_deterministic(self, raw_ticket):
        run = run_agent_pipeline(raw_ticket, registry=make_mock_registry())
        types = [e.event_type for e in run.events]
        assert types[0] == AgentEventType.RUN_STARTED
        assert types[1] == AgentEventType.PLAN_CREATED
        # TOOL_CALLED and TOOL_RETURNED interleaved, but RUN_COMPLETED must be last
        assert types[-1] == AgentEventType.RUN_COMPLETED


# ---------------------------------------------------------------------------
# Human review routing
# ---------------------------------------------------------------------------


class TestHumanReview:
    def test_human_review_when_risk_high(self, raw_ticket):
        reg = make_mock_registry(risk_assessment=_RISK_HIGH)
        run = run_agent_pipeline(raw_ticket, registry=reg)
        assert run.final_status == AgentRunStatus.HUMAN_REVIEW_REQUIRED

    def test_human_review_when_draft_unsupported(self, raw_ticket):
        reg = make_mock_registry(draft_reply=_DRAFT_REVIEW)
        run = run_agent_pipeline(raw_ticket, registry=reg)
        assert run.final_status == AgentRunStatus.HUMAN_REVIEW_REQUIRED

    def test_human_review_event_recorded(self, raw_ticket):
        reg = make_mock_registry(risk_assessment=_RISK_HIGH)
        run = run_agent_pipeline(raw_ticket, registry=reg)
        types = [e.event_type for e in run.events]
        assert AgentEventType.HUMAN_REVIEW_REQUIRED in types


# ---------------------------------------------------------------------------
# Failure handling
# ---------------------------------------------------------------------------


class TestFailure:
    def test_status_failed_on_tool_error(self, raw_ticket):
        reg = make_mock_registry(fail_tool="classify_ticket")
        run = run_agent_pipeline(raw_ticket, registry=reg)
        assert run.final_status == AgentRunStatus.FAILED

    def test_run_failed_event_recorded(self, raw_ticket):
        reg = make_mock_registry(fail_tool="classify_ticket")
        run = run_agent_pipeline(raw_ticket, registry=reg)
        types = [e.event_type for e in run.events]
        assert AgentEventType.RUN_FAILED in types

    def test_ticket_output_none_on_early_failure(self, raw_ticket):
        reg = make_mock_registry(fail_tool="normalize_ticket")
        run = run_agent_pipeline(raw_ticket, registry=reg)
        assert run.ticket_output is None

    def test_draft_reply_none_on_failure(self, raw_ticket):
        reg = make_mock_registry(fail_tool="assess_risk")
        run = run_agent_pipeline(raw_ticket, registry=reg)
        assert run.draft_reply is None


# ---------------------------------------------------------------------------
# Custom injectables
# ---------------------------------------------------------------------------


class TestInjectables:
    def test_custom_registry_used(self, raw_ticket):
        """Provided registry is used instead of default."""
        reg = make_mock_registry(fail_tool="normalize_ticket")
        run = run_agent_pipeline(raw_ticket, registry=reg)
        # If the custom registry wasn't used, the real normalize_ticket
        # would succeed; failure proves our registry was used.
        assert run.final_status == AgentRunStatus.FAILED

    def test_custom_planner_used(self, raw_ticket):
        """Provided planner is used instead of default."""

        class CustomPlanner(DeterministicTaskPlanner):
            def select_template(self, text: str) -> str:
                return "complaint_escalation"

        run = run_agent_pipeline(
            raw_ticket,
            planner=CustomPlanner(),
            registry=make_mock_registry(),
        )
        assert run.plan is not None
        assert "complaint" in run.plan.goal.lower()


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_started_at_and_completed_at_set(self, raw_ticket):
        run = run_agent_pipeline(raw_ticket, registry=make_mock_registry())
        assert run.started_at is not None
        assert run.completed_at is not None
        assert run.completed_at >= run.started_at

    def test_raw_ticket_text_preserved(self, raw_ticket):
        run = run_agent_pipeline(raw_ticket, registry=make_mock_registry())
        assert run.raw_ticket_text == "我要退款"
