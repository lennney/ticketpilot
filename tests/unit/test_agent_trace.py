"""Unit tests for AgentTrace (Batch 1)."""

import json

import pytest

from ticketpilot.agent.schemas import AgentEventType
from ticketpilot.agent.trace import AgentTrace


class TestAgentTrace:
    def test_empty_trace_has_zero_events(self):
        trace = AgentTrace("run_001")
        assert trace.count() == 0
        assert trace.get_events() == []
        assert trace.last_event() is None

    def test_add_event_records_one_event(self):
        trace = AgentTrace("run_001")
        event = trace.add_event(AgentEventType.RUN_STARTED)
        assert event.event_type == AgentEventType.RUN_STARTED
        assert trace.count() == 1

    def test_events_recorded_in_order(self):
        trace = AgentTrace("run_001")
        trace.add_event(AgentEventType.RUN_STARTED)
        trace.add_event(AgentEventType.PLAN_CREATED)
        trace.add_event(AgentEventType.TOOL_CALLED, data={"tool": "classify"})
        events = trace.get_events()
        assert len(events) == 3
        assert events[0].event_type == AgentEventType.RUN_STARTED
        assert events[1].event_type == AgentEventType.PLAN_CREATED
        assert events[2].event_type == AgentEventType.TOOL_CALLED

    def test_get_events_returns_copy(self):
        trace = AgentTrace("run_001")
        trace.add_event(AgentEventType.RUN_STARTED)
        events_copy = trace.get_events()
        events_copy.append("mutated")  # should not affect internal list
        assert trace.count() == 1  # internal unchanged

    def test_last_event_returns_latest(self):
        trace = AgentTrace("run_001")
        trace.add_event(AgentEventType.RUN_STARTED)
        trace.add_event(AgentEventType.PLAN_CREATED)
        last = trace.last_event()
        assert last is not None
        assert last.event_type == AgentEventType.PLAN_CREATED

    def test_count_returns_correct_number(self):
        trace = AgentTrace("run_001")
        assert trace.count() == 0
        trace.add_event(AgentEventType.RUN_STARTED)
        assert trace.count() == 1
        trace.add_event(AgentEventType.PLAN_CREATED)
        assert trace.count() == 2
        trace.add_event(AgentEventType.RUN_COMPLETED)
        assert trace.count() == 3

    def test_to_dict_includes_run_id_and_events(self):
        trace = AgentTrace("run_001")
        trace.add_event(AgentEventType.RUN_STARTED)
        d = trace.to_dict()
        assert d["run_id"] == "run_001"
        assert d["event_count"] == 1
        assert len(d["events"]) == 1
        assert d["events"][0]["event_type"] == "run_started"

    def test_to_json_returns_valid_json(self):
        trace = AgentTrace("run_001")
        trace.add_event(AgentEventType.RUN_STARTED, data={"key": "value"})
        trace.add_event(AgentEventType.RUN_COMPLETED)
        raw = trace.to_json()
        parsed = json.loads(raw)
        assert parsed["run_id"] == "run_001"
        assert parsed["event_count"] == 2
        assert len(parsed["events"]) == 2

    def test_add_event_supports_step_number(self):
        trace = AgentTrace("run_001")
        event = trace.add_event(AgentEventType.TOOL_CALLED, step_number=3)
        assert event.step_number == 3

    def test_add_event_supports_default_empty_data(self):
        trace = AgentTrace("run_001")
        event = trace.add_event(AgentEventType.RUN_STARTED)
        assert event.data == {}

    def test_trace_rejects_empty_run_id(self):
        with pytest.raises(ValueError, match="run_id must not be empty"):
            AgentTrace("")

    def test_trace_rejects_whitespace_run_id(self):
        with pytest.raises(ValueError, match="run_id must not be empty"):
            AgentTrace("   ")

    def test_multiple_traces_are_independent(self):
        trace_a = AgentTrace("run_a")
        trace_b = AgentTrace("run_b")
        trace_a.add_event(AgentEventType.RUN_STARTED)
        assert trace_a.count() == 1
        assert trace_b.count() == 0

    def test_to_dict_event_has_expected_keys(self):
        trace = AgentTrace("run_001")
        trace.add_event(
            AgentEventType.TOOL_RETURNED, data={"result": "ok"}, step_number=2
        )
        d = trace.to_dict()
        event = d["events"][0]
        assert "event_type" in event
        assert "timestamp" in event
        assert "step_number" in event
        assert "data" in event
        assert event["step_number"] == 2
        assert event["data"]["result"] == "ok"
