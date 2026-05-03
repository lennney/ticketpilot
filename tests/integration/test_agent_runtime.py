"""Integration tests for the deterministic Agent Kernel Runtime (run_agent_pipeline).

Tests exercise run_agent_pipeline() through real tools, including DB-backed
retrieval.  All tests fail (never skip) when the database is unavailable so
that the "0 skipped" requirement is enforced.
"""

from __future__ import annotations

import json
from datetime import datetime

import pytest

from ticketpilot.agent.loop import run_agent_pipeline
from ticketpilot.agent.schemas import (
    AgentEventType,
    AgentRun,
    AgentRunStatus,
)
from ticketpilot.schema.ticket import RawTicket


def _db_is_available() -> bool:
    try:
        from ticketpilot.retrieval.db.connection import get_db_connection
        with get_db_connection() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception:
        return False


def _seed_db() -> None:
    try:
        from ticketpilot.retrieval.db.seeding import get_chunk_count, seed_knowledge_chunks
        if get_chunk_count() == 0:
            seed_knowledge_chunks(clear_existing=True)
    except Exception:
        pass


def _make_ticket(text: str, label: str = "test") -> RawTicket:
    return RawTicket(
        original_text=text,
        submitted_at=datetime(2026, 5, 3, 12, 0, 0),
        customer_id=f"test-agent-runtime-{label}",
    )


REFUND = "我申请退款，订单号123456"
COMPLAINT = "律师函警告 我要起诉你们 要求赔偿"
ACCOUNT = "我的账号被盗了，有人盗刷了我的订单"
WEAK = "hello world unusual query"


class TestRefundTicketAgentRun:

    @pytest.fixture(autouse=True)
    def _require_db(self) -> None:
        if not _db_is_available():
            pytest.fail("Database not available")
        _seed_db()

    def test_agent_run_shape(self) -> None:
        run = run_agent_pipeline(_make_ticket(REFUND, "refund"))
        assert isinstance(run, AgentRun)
        assert run.run_id is not None
        assert len(run.run_id) > 0
        assert run.raw_ticket_text == REFUND
        assert run.plan is not None
        assert len(run.plan.steps) == 5
        assert len(run.events) > 0
        assert run.final_status in (AgentRunStatus.COMPLETED, AgentRunStatus.HUMAN_REVIEW_REQUIRED, AgentRunStatus.FAILED)
        assert run.started_at is not None
        assert run.completed_at is not None
        assert run.completed_at >= run.started_at

    def test_event_ordering(self) -> None:
        run = run_agent_pipeline(_make_ticket(REFUND, "refund-ord"))
        types = [e.event_type for e in run.events]
        assert types[0] == AgentEventType.RUN_STARTED
        assert types.index(AgentEventType.RUN_STARTED) < types.index(AgentEventType.PLAN_CREATED)
        assert types.index(AgentEventType.PLAN_CREATED) < types.index(AgentEventType.TOOL_CALLED)
        assert types[-1] in (AgentEventType.RUN_COMPLETED, AgentEventType.RUN_FAILED)
        assert sum(1 for t in types if t == AgentEventType.TOOL_CALLED) == 5
        assert sum(1 for t in types if t == AgentEventType.TOOL_RETURNED) == 5

    def test_plan_has_deterministic_steps(self) -> None:
        run = run_agent_pipeline(_make_ticket(REFUND, "refund-plan"))
        assert run.plan is not None
        assert [s.step_id for s in run.plan.steps] == ["s1_normalize", "s2_classify", "s3_assess_risk", "s4_retrieve_evidence", "s5_generate_draft"]
        assert [s.tool_name for s in run.plan.steps] == ["normalize_ticket", "classify_ticket", "assess_risk", "retrieve_evidence", "generate_draft"]

    def test_plan_goal_matches_refund(self) -> None:
        run = run_agent_pipeline(_make_ticket(REFUND, "refund-goal"))
        assert run.plan is not None
        assert "refund" in run.plan.goal.lower()

    def test_constraints_no_auto_send(self) -> None:
        run = run_agent_pipeline(_make_ticket(REFUND, "refund-cnst"))
        assert run.plan is not None
        assert any("no auto-send" in c.lower() for c in run.plan.constraints)

    def test_ticket_output_attached(self) -> None:
        run = run_agent_pipeline(_make_ticket(REFUND, "refund-out"))
        assert run.ticket_output is not None
        assert run.ticket_output["ticket_id"] == run.run_id
        assert run.ticket_output["raw_ticket"]["original_text"] == REFUND

    def test_draft_reply_attached(self) -> None:
        run = run_agent_pipeline(_make_ticket(REFUND, "refund-dr"))
        assert run.draft_reply is not None
        assert isinstance(run.draft_reply["draft_text"], str)
        assert len(run.draft_reply["draft_text"]) > 0
        assert "confidence" in run.draft_reply

    def test_trace_json_serializable(self) -> None:
        run = run_agent_pipeline(_make_ticket(REFUND, "refund-json"))
        events = [e.model_dump(mode="json") for e in run.events]
        p = {"run_id": run.run_id, "events": events, "event_count": len(events)}
        d = json.loads(json.dumps(p, ensure_ascii=False))
        assert d["run_id"] == run.run_id
        assert d["event_count"] == len(run.events)

    def test_tool_events_have_data(self) -> None:
        run = run_agent_pipeline(_make_ticket(REFUND, "refund-td"))
        for event in run.events:
            if event.event_type == AgentEventType.TOOL_CALLED:
                assert "tool" in event.data
                assert "step" in event.data

    def test_not_failed(self) -> None:
        run = run_agent_pipeline(_make_ticket(REFUND, "refund-nf"))
        assert run.final_status != AgentRunStatus.FAILED


class TestHighRiskComplaintTicket:

    @pytest.fixture(autouse=True)
    def _require_db(self) -> None:
        if not _db_is_available():
            pytest.fail("Database not available")
        _seed_db()

    def test_human_review_required(self) -> None:
        run = run_agent_pipeline(_make_ticket(COMPLAINT, "hr"))
        assert run.final_status == AgentRunStatus.HUMAN_REVIEW_REQUIRED

    def test_human_review_event(self) -> None:
        run = run_agent_pipeline(_make_ticket(COMPLAINT, "hr-ev"))
        assert AgentEventType.HUMAN_REVIEW_REQUIRED in [e.event_type for e in run.events]

    def test_risk_checked_must_review(self) -> None:
        run = run_agent_pipeline(_make_ticket(COMPLAINT, "hr-rc"))
        for e in run.events:
            if e.event_type == AgentEventType.RISK_CHECKED:
                assert e.data.get("must_human_review") is True
                break
        else:
            pytest.fail("RISK_CHECKED not found")

    def test_draft_must_review(self) -> None:
        run = run_agent_pipeline(_make_ticket(COMPLAINT, "hr-dr"))
        assert run.draft_reply is not None
        assert run.draft_reply.get("must_human_review") is True

    def test_event_ordering(self) -> None:
        run = run_agent_pipeline(_make_ticket(COMPLAINT, "hr-ord"))
        types = [e.event_type for e in run.events]
        assert types[0] == AgentEventType.RUN_STARTED
        assert types.index(AgentEventType.RUN_STARTED) < types.index(AgentEventType.PLAN_CREATED)
        assert types.index(AgentEventType.PLAN_CREATED) < types.index(AgentEventType.TOOL_CALLED)
        assert types.index(AgentEventType.HUMAN_REVIEW_REQUIRED) < types.index(AgentEventType.RUN_COMPLETED)
        assert types[-1] == AgentEventType.RUN_COMPLETED

    def test_plan_goal(self) -> None:
        run = run_agent_pipeline(_make_ticket(COMPLAINT, "hr-goal"))
        gl = run.plan.goal.lower()
        assert "complaint" in gl or "legal" in gl or "escalation" in gl

    def test_constraints(self) -> None:
        run = run_agent_pipeline(_make_ticket(COMPLAINT, "hr-cnst"))
        cl = [c.lower() for c in run.plan.constraints]
        assert any("no auto-send" in c for c in cl)
        assert any("human review" in c for c in cl)

    def test_success_criteria(self) -> None:
        run = run_agent_pipeline(_make_ticket(COMPLAINT, "hr-sc"))
        assert "escalation" in " ".join(run.plan.success_criteria).lower()

    def test_trace_json(self) -> None:
        run = run_agent_pipeline(_make_ticket(COMPLAINT, "hr-json"))
        p = {"run_id": run.run_id, "events": [e.model_dump(mode="json") for e in run.events], "final_status": run.final_status.value}
        d = json.loads(json.dumps(p, ensure_ascii=False))
        assert d["final_status"] == "human_review_required"

    def test_shape(self) -> None:
        run = run_agent_pipeline(_make_ticket(COMPLAINT, "hr-shape"))
        assert isinstance(run, AgentRun)
        assert len(run.plan.steps) == 5
        assert len(run.events) > 0


class TestAccountSecurityTicket:

    @pytest.fixture(autouse=True)
    def _require_db(self) -> None:
        if not _db_is_available():
            pytest.fail("Database not available")
        _seed_db()

    def test_agent_run_shape(self) -> None:
        run = run_agent_pipeline(_make_ticket(ACCOUNT, "acct"))
        assert isinstance(run, AgentRun)
        assert run.run_id is not None
        assert run.raw_ticket_text == ACCOUNT
        assert run.plan is not None
        assert len(run.plan.steps) == 5
        assert len(run.events) > 0
        assert run.final_status in (AgentRunStatus.COMPLETED, AgentRunStatus.HUMAN_REVIEW_REQUIRED, AgentRunStatus.FAILED)

    def test_plan_steps(self) -> None:
        run = run_agent_pipeline(_make_ticket(ACCOUNT, "acct-plan"))
        assert [s.tool_name for s in run.plan.steps] == ["normalize_ticket", "classify_ticket", "assess_risk", "retrieve_evidence", "generate_draft"]

    def test_plan_goal(self) -> None:
        run = run_agent_pipeline(_make_ticket(ACCOUNT, "acct-goal"))
        gl = run.plan.goal.lower()
        assert "account" in gl or "login" in gl

    def test_event_ordering(self) -> None:
        run = run_agent_pipeline(_make_ticket(ACCOUNT, "acct-ord"))
        types = [e.event_type for e in run.events]
        assert types[0] == AgentEventType.RUN_STARTED
        assert types.index(AgentEventType.RUN_STARTED) < types.index(AgentEventType.PLAN_CREATED)
        assert types.index(AgentEventType.PLAN_CREATED) < types.index(AgentEventType.TOOL_CALLED)
        assert types[-1] in (AgentEventType.RUN_COMPLETED, AgentEventType.RUN_FAILED)

    def test_draft(self) -> None:
        run = run_agent_pipeline(_make_ticket(ACCOUNT, "acct-dr"))
        assert run.draft_reply is not None
        assert isinstance(run.draft_reply.get("draft_text"), str)
        assert len(run.draft_reply["draft_text"]) > 0

    def test_evidence_list(self) -> None:
        run = run_agent_pipeline(_make_ticket(ACCOUNT, "acct-ev"))
        assert isinstance(run.ticket_output.get("evidence_candidates", []), list)

    def test_trace_json(self) -> None:
        run = run_agent_pipeline(_make_ticket(ACCOUNT, "acct-json"))
        d = {"run_id": run.run_id, "events": [e.model_dump(mode="json") for e in run.events]}
        assert json.loads(json.dumps(d, ensure_ascii=False))["run_id"] == run.run_id


class TestCrossCutting:

    @pytest.fixture(autouse=True)
    def _require_db(self) -> None:
        if not _db_is_available():
            pytest.fail("Database not available")
        _seed_db()

    @staticmethod
    def _run_all():
        for label, text in [("refund", REFUND), ("complaint", COMPLAINT), ("account", ACCOUNT)]:
            yield label, run_agent_pipeline(_make_ticket(text, f"cc-{label}"))

    def test_no_auto_send(self) -> None:
        for label, run in self._run_all():
            for event in run.events:
                assert "auto_send" not in str(event.event_type.value).lower()
                assert "auto_send" not in str(event.data).lower()

    def test_no_llm(self) -> None:
        for label, run in self._run_all():
            for ok in ("draft_reply", "ticket_output"):
                out = getattr(run, ok, None)
                if isinstance(out, dict):
                    for fk in ("model", "provider", "api_key", "llm"):
                        assert fk not in out
            for event in run.events:
                if event.event_type == AgentEventType.RUN_FAILED:
                    err = str(event.data.get("error", "")).lower()
                    assert "connection" not in err
                    assert "timeout" not in err

    def test_no_evidence_fallback(self) -> None:
        run = run_agent_pipeline(_make_ticket(WEAK, "cc-nev"))
        assert isinstance(run, AgentRun)
        assert run.final_status in (AgentRunStatus.COMPLETED, AgentRunStatus.HUMAN_REVIEW_REQUIRED, AgentRunStatus.FAILED)

    def test_weak_no_crash(self) -> None:
        run = run_agent_pipeline(_make_ticket("zzz xxx yyy", "cc-weak"))
        assert isinstance(run, AgentRun)
        assert run.final_status in (AgentRunStatus.COMPLETED, AgentRunStatus.HUMAN_REVIEW_REQUIRED, AgentRunStatus.FAILED)

    def test_skill_id_none(self) -> None:
        for label, run in self._run_all():
            assert run.skill_id is None

    def test_review_decision_none(self) -> None:
        for label, run in self._run_all():
            assert run.review_decision is None

    def test_not_failed(self) -> None:
        run = run_agent_pipeline(_make_ticket(REFUND, "cc-nf"))
        assert run.final_status != AgentRunStatus.FAILED
