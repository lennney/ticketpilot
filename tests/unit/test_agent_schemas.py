"""Unit tests for Agent Kernel schemas (Batch 1)."""

from datetime import datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from ticketpilot.agent.schemas import (
    AgentEvent,
    AgentEventType,
    AgentPlan,
    AgentRun,
    AgentRunStatus,
    AgentStep,
    AgentToolSpec,
)


class TestAgentEventType:
    def test_has_ten_values(self):
        assert len(AgentEventType) == 10

    def test_run_started_value(self):
        assert AgentEventType.RUN_STARTED.value == "run_started"

    def test_run_failed_value(self):
        assert AgentEventType.RUN_FAILED.value == "run_failed"


class TestAgentRunStatus:
    def test_has_five_values(self):
        assert len(AgentRunStatus) == 6

    def test_created_default(self):
        assert AgentRunStatus.CREATED.value == "created"

    def test_human_review_required_value(self):
        assert AgentRunStatus.HUMAN_REVIEW_REQUIRED.value == "human_review_required"


class TestAgentEvent:
    def test_valid_construction(self):
        event = AgentEvent(event_type=AgentEventType.RUN_STARTED)
        assert event.event_type == AgentEventType.RUN_STARTED
        assert event.data == {}
        assert event.step_number is None
        assert isinstance(event.timestamp, datetime)

    def test_with_data_and_step(self):
        event = AgentEvent(
            event_type=AgentEventType.TOOL_CALLED,
            data={"tool": "classify_ticket", "input": "退款"},
            step_number=1,
        )
        assert event.event_type == AgentEventType.TOOL_CALLED
        assert event.data["tool"] == "classify_ticket"
        assert event.step_number == 1

    def test_rejects_negative_step_number(self):
        with pytest.raises(ValidationError):
            AgentEvent(event_type=AgentEventType.RUN_STARTED, step_number=-1)

    def test_zero_step_number_allowed(self):
        event = AgentEvent(event_type=AgentEventType.RUN_STARTED, step_number=0)
        assert event.step_number == 0

    def test_timestamp_defaults_to_utcnow(self):
        event = AgentEvent(event_type=AgentEventType.RUN_STARTED)
        assert event.timestamp is not None
        # Should be close to now
        now = datetime.now(timezone.utc)
        diff = abs((now - event.timestamp).total_seconds())
        assert diff < 5


class TestAgentToolSpec:
    def test_valid_construction(self):
        spec = AgentToolSpec(
            name="classify_ticket",
            description="Classify a ticket into 8 intent categories",
            input_schema={"type": "object", "properties": {"text": {"type": "string"}}},
            output_schema={"type": "object", "properties": {"intent": {"type": "string"}}},
            risk_level="low",
        )
        assert spec.name == "classify_ticket"
        assert spec.risk_level == "low"

    def test_default_schemas_are_empty_dict(self):
        spec = AgentToolSpec(name="test", description="test tool", risk_level="low")
        assert spec.input_schema == {}
        assert spec.output_schema == {}

    def test_rejects_empty_name(self):
        with pytest.raises(ValidationError):
            AgentToolSpec(name="", description="desc", risk_level="low")

    def test_rejects_whitespace_name(self):
        with pytest.raises(ValidationError):
            AgentToolSpec(name="   ", description="desc", risk_level="low")

    def test_rejects_empty_description(self):
        with pytest.raises(ValidationError):
            AgentToolSpec(name="test", description="", risk_level="low")

    def test_rejects_invalid_risk_level(self):
        with pytest.raises(ValidationError):
            AgentToolSpec(name="test", description="desc", risk_level="critical")

    def test_accepts_all_valid_risk_levels(self):
        for level in ["low", "medium", "high"]:
            spec = AgentToolSpec(name="test", description="desc", risk_level=level)
            assert spec.risk_level == level


class TestAgentStep:
    def test_valid_construction(self):
        step = AgentStep(
            step_id="s1",
            description="Normalize ticket text",
            tool_name="normalize_ticket",
            expected_output="NormalizedTicket",
        )
        assert step.step_id == "s1"
        assert step.tool_name == "normalize_ticket"
        assert step.fallback is None

    def test_with_optionals(self):
        step = AgentStep(
            step_id="s1",
            description="Classify ticket",
            tool_name="classify_ticket",
            input_params={"text": "退款"},
            expected_output="ClassificationResult",
            fallback="default to OTHER",
        )
        assert step.input_params == {"text": "退款"}
        assert step.fallback == "default to OTHER"

    def test_rejects_empty_step_id(self):
        with pytest.raises(ValidationError):
            AgentStep(
                step_id="",
                description="desc",
                tool_name="tool",
                expected_output="out",
            )

    def test_rejects_empty_tool_name(self):
        with pytest.raises(ValidationError):
            AgentStep(
                step_id="s1",
                description="desc",
                tool_name="",
                expected_output="out",
            )

    def test_rejects_empty_expected_output(self):
        with pytest.raises(ValidationError):
            AgentStep(
                step_id="s1",
                description="desc",
                tool_name="tool",
                expected_output="",
            )


class TestAgentPlan:
    def test_valid_construction(self):
        step = AgentStep(
            step_id="s1",
            description="Classify",
            tool_name="classify_ticket",
            expected_output="ClassificationResult",
        )
        plan = AgentPlan(
            goal="Process a refund ticket",
            steps=[step],
            required_tools=["classify_ticket"],
            success_criteria=["intent identified"],
        )
        assert plan.goal == "Process a refund ticket"
        assert len(plan.steps) == 1
        assert len(plan.required_tools) == 1

    def test_rejects_empty_goal(self):
        step = AgentStep(
            step_id="s1", description="d", tool_name="t", expected_output="o"
        )
        with pytest.raises(ValidationError):
            AgentPlan(goal="", steps=[step])

    def test_rejects_empty_steps(self):
        with pytest.raises(ValidationError):
            AgentPlan(goal="goal", steps=[])

    def test_rejects_duplicate_step_ids(self):
        step_a = AgentStep(
            step_id="s1", description="d", tool_name="t", expected_output="o"
        )
        step_b = AgentStep(
            step_id="s1", description="d", tool_name="t", expected_output="o"
        )
        with pytest.raises(ValidationError):
            AgentPlan(goal="goal", steps=[step_a, step_b])

    def test_rejects_duplicate_required_tools(self):
        step = AgentStep(
            step_id="s1", description="d", tool_name="t", expected_output="o"
        )
        with pytest.raises(ValidationError):
            AgentPlan(
                goal="goal",
                steps=[step],
                required_tools=["classify", "classify"],
            )

    def test_allows_multiple_steps(self):
        steps = [
            AgentStep(step_id="s1", description="d1", tool_name="t1", expected_output="o1"),
            AgentStep(step_id="s2", description="d2", tool_name="t2", expected_output="o2"),
        ]
        plan = AgentPlan(goal="goal", steps=steps)
        assert len(plan.steps) == 2

    def test_default_lists_are_empty(self):
        step = AgentStep(
            step_id="s1", description="d", tool_name="t", expected_output="o"
        )
        plan = AgentPlan(goal="goal", steps=[step])
        assert plan.constraints == []
        assert plan.required_tools == []
        assert plan.success_criteria == []


class TestAgentRun:
    def test_initial_state(self):
        run = AgentRun(run_id="run_001", raw_ticket_text="我要退款")
        assert run.run_id == "run_001"
        assert run.raw_ticket_text == "我要退款"
        assert run.final_status == AgentRunStatus.CREATED
        assert run.plan is None
        assert run.events == []

    def test_with_full_data(self):
        step = AgentStep(
            step_id="s1", description="d", tool_name="t", expected_output="o"
        )
        plan = AgentPlan(goal="goal", steps=[step])
        now = datetime.now(timezone.utc)
        run = AgentRun(
            run_id="run_002",
            raw_ticket_text="投诉",
            plan=plan,
            skill_id="complaint_escalation",
            final_status=AgentRunStatus.RUNNING,
            started_at=now,
        )
        assert run.plan is not None
        assert run.skill_id == "complaint_escalation"
        assert run.final_status == AgentRunStatus.RUNNING

    def test_rejects_empty_run_id(self):
        with pytest.raises(ValidationError):
            AgentRun(run_id="", raw_ticket_text="text")

    def test_rejects_whitespace_run_id(self):
        with pytest.raises(ValidationError):
            AgentRun(run_id="   ", raw_ticket_text="text")

    def test_rejects_empty_raw_ticket_text(self):
        with pytest.raises(ValidationError):
            AgentRun(run_id="r1", raw_ticket_text="")

    def test_json_serialization_round_trip(self):
        run = AgentRun(run_id="run_003", raw_ticket_text="我要退款，订单号：123456")
        dumped = run.model_dump(mode="json")
        assert dumped["run_id"] == "run_003"
        assert dumped["raw_ticket_text"] == "我要退款，订单号：123456"
        assert dumped["final_status"] == "created"
        assert dumped["plan"] is None

        loaded = AgentRun.model_validate(dumped)
        assert loaded.run_id == run.run_id
        assert loaded.raw_ticket_text == run.raw_ticket_text
        assert loaded.final_status == run.final_status

    def test_rejects_completed_at_before_started_at(self):
        now = datetime.now(timezone.utc)
        earlier = now - timedelta(hours=1)
        with pytest.raises(ValidationError):
            AgentRun(
                run_id="r1",
                raw_ticket_text="text",
                started_at=now,
                completed_at=earlier,
            )

    def test_allows_completed_at_after_started_at(self):
        now = datetime.now(timezone.utc)
        later = now + timedelta(seconds=5)
        run = AgentRun(
            run_id="r1",
            raw_ticket_text="text",
            started_at=now,
            completed_at=later,
        )
        assert run.completed_at == later

    def test_default_ticket_output_is_none(self):
        run = AgentRun(run_id="r1", raw_ticket_text="text")
        assert run.ticket_output is None
        assert run.draft_reply is None
        assert run.review_decision is None
