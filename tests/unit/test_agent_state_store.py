"""Tests for AgentStateStore — SQLite-backed agent run persistence.

Factor 6: Launch / Pause / Resume
"""

import uuid
from datetime import datetime

import pytest

from ticketpilot.agent.schemas import (
    AgentEvent,
    AgentEventType,
    AgentPlan,
    AgentRun,
    AgentRunStatus,
    AgentStep,
)
from ticketpilot.agent.state_store import AgentStateStore


class TestAgentStateStore:
    """Tests for AgentStateStore CRUD and lifecycle."""

    def _make_run(
        self,
        status: AgentRunStatus = AgentRunStatus.RUNNING,
        run_id: str | None = None,
    ) -> AgentRun:
        """Helper to create AgentRun."""
        return AgentRun(
            run_id=run_id or str(uuid.uuid4()),
            raw_ticket_text="测试工单：退款申请",
            plan=AgentPlan(
                goal="处理退款",
                steps=[
                    AgentStep(
                        step_id="s1",
                        description="归一化",
                        tool_name="normalize_ticket",
                        expected_output="NormalizedTicket",
                    ),
                ],
            ),
            events=[
                AgentEvent(event_type=AgentEventType.RUN_STARTED),
                AgentEvent(event_type=AgentEventType.PLAN_CREATED, step_number=0),
            ],
            ticket_output={"ticket_id": "test-001"},
            draft_reply={"draft_text": "退款将在3个工作日内处理[1]。", "confidence": 0.85},
            final_status=status,
            started_at=datetime.utcnow(),
        )

    def test_save_and_load(self, tmp_path):
        """Can save and load an AgentRun."""
        store = AgentStateStore(tmp_path / "test.db")
        run = self._make_run()
        store.save_run(run)

        loaded = store.load_run(run.run_id)
        assert loaded is not None
        assert loaded.run_id == run.run_id
        assert loaded.raw_ticket_text == run.raw_ticket_text
        assert loaded.final_status == AgentRunStatus.RUNNING

    def test_load_nonexistent(self, tmp_path):
        """Returns None for unknown run_id."""
        store = AgentStateStore(tmp_path / "test.db")
        assert store.load_run("nonexistent") is None

    def test_save_overwrites(self, tmp_path):
        """Saving same run_id overwrites the previous record."""
        store = AgentStateStore(tmp_path / "test.db")
        run = self._make_run()
        store.save_run(run)

        # Update status and save again
        run.final_status = AgentRunStatus.COMPLETED
        store.save_run(run)

        loaded = store.load_run(run.run_id)
        assert loaded.final_status == AgentRunStatus.COMPLETED

    def test_pause_run(self, tmp_path):
        """Can pause a running agent."""
        store = AgentStateStore(tmp_path / "test.db")
        run = self._make_run(status=AgentRunStatus.RUNNING)
        store.save_run(run)

        store.pause_run(run.run_id, reason="waiting_for_human_input")

        loaded = store.load_run(run.run_id)
        assert loaded.final_status == AgentRunStatus.PAUSED

    def test_resume_run(self, tmp_path):
        """Can resume a paused agent with human input."""
        store = AgentStateStore(tmp_path / "test.db")
        run = self._make_run(status=AgentRunStatus.PAUSED)
        store.save_run(run)

        human_input = {"decision": "approve", "comment": "同意退款"}
        resumed = store.resume_run(run.run_id, human_input)

        assert resumed.final_status == AgentRunStatus.RUNNING
        assert resumed.review_decision == human_input

    def test_resume_non_paused_raises(self, tmp_path):
        """Cannot resume a non-paused run."""
        store = AgentStateStore(tmp_path / "test.db")
        run = self._make_run(status=AgentRunStatus.COMPLETED)
        store.save_run(run)

        with pytest.raises(ValueError, match="not paused"):
            store.resume_run(run.run_id, {"decision": "approve"})

    def test_list_paused(self, tmp_path):
        """Can list all paused runs."""
        store = AgentStateStore(tmp_path / "test.db")

        run1 = self._make_run(status=AgentRunStatus.PAUSED)
        run2 = self._make_run(status=AgentRunStatus.RUNNING)
        run3 = self._make_run(status=AgentRunStatus.PAUSED)

        store.save_run(run1)
        store.save_run(run2)
        store.save_run(run3)

        paused = store.list_paused()
        assert len(paused) == 2
        paused_ids = {r.run_id for r in paused}
        assert run1.run_id in paused_ids
        assert run3.run_id in paused_ids

    def test_list_runs(self, tmp_path):
        """Can list all runs with optional status filter."""
        store = AgentStateStore(tmp_path / "test.db")

        store.save_run(self._make_run(status=AgentRunStatus.RUNNING))
        store.save_run(self._make_run(status=AgentRunStatus.COMPLETED))
        store.save_run(self._make_run(status=AgentRunStatus.PAUSED))

        all_runs = store.list_runs()
        assert len(all_runs) == 3

        completed = store.list_runs(status=AgentRunStatus.COMPLETED)
        assert len(completed) == 1

    def test_delete_run(self, tmp_path):
        """Can delete a run."""
        store = AgentStateStore(tmp_path / "test.db")
        run = self._make_run()
        store.save_run(run)
        assert store.load_run(run.run_id) is not None

        store.delete_run(run.run_id)
        assert store.load_run(run.run_id) is None

    def test_events_preserved(self, tmp_path):
        """Events survive save/load roundtrip."""
        store = AgentStateStore(tmp_path / "test.db")
        run = self._make_run()
        run.events.append(AgentEvent(
            event_type=AgentEventType.TOOL_CALLED,
            step_number=1,
            data={"tool": "normalize_ticket"},
        ))
        store.save_run(run)

        loaded = store.load_run(run.run_id)
        assert len(loaded.events) == 3
        assert loaded.events[2].event_type == AgentEventType.TOOL_CALLED
        assert loaded.events[2].data["tool"] == "normalize_ticket"

    def test_plan_preserved(self, tmp_path):
        """Plan survives save/load roundtrip."""
        store = AgentStateStore(tmp_path / "test.db")
        run = self._make_run()
        store.save_run(run)

        loaded = store.load_run(run.run_id)
        assert loaded.plan is not None
        assert loaded.plan.goal == "处理退款"
        assert len(loaded.plan.steps) == 1
