"""Pydantic schemas for the Agent Kernel runtime.

Batch 1: data contracts and trace event models only.
No runtime execution logic.
"""

from __future__ import annotations

from datetime import datetime, timezone, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator, model_validator


class AgentEventType(str, Enum):
    """Types of events that can occur during an agent run."""

    RUN_STARTED = "run_started"
    PLAN_CREATED = "plan_created"
    SKILL_SELECTED = "skill_selected"
    TOOL_CALLED = "tool_called"
    TOOL_RETURNED = "tool_returned"
    DRAFT_GENERATED = "draft_generated"
    RISK_CHECKED = "risk_checked"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"


class AgentRunStatus(str, Enum):
    """Status values for an agent run lifecycle."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


_VALID_RISK_LEVELS = frozenset({"low", "medium", "high"})


class AgentEvent(BaseModel):
    """A single event recorded during an agent run."""

    event_type: AgentEventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    step_number: int | None = None
    data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("step_number")
    @classmethod
    def _step_number_must_be_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("step_number must be >= 0")
        return v


class AgentToolSpec(BaseModel):
    """Data-only specification for a registrable agent tool.

    Runtime callable binding belongs to the Tool Registry (Batch 2).
    """

    name: str
    description: str
    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "low"

    @field_validator("name", "description")
    @classmethod
    def _must_not_be_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @field_validator("risk_level")
    @classmethod
    def _risk_level_must_be_valid(cls, v: str) -> str:
        if v not in _VALID_RISK_LEVELS:
            raise ValueError(
                f"risk_level must be one of {sorted(_VALID_RISK_LEVELS)}, got '{v}'"
            )
        return v


class AgentStep(BaseModel):
    """A single step within an agent plan."""

    step_id: str
    description: str
    tool_name: str
    input_params: dict[str, Any] = Field(default_factory=dict)
    expected_output: str
    fallback: str | None = None

    @field_validator("step_id", "description", "tool_name", "expected_output")
    @classmethod
    def _must_not_be_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped


class AgentPlan(BaseModel):
    """Structured plan for an agent run."""

    goal: str
    constraints: list[str] = Field(default_factory=list)
    steps: list[AgentStep]
    required_tools: list[str] = Field(default_factory=list)
    success_criteria: list[str] = Field(default_factory=list)

    @field_validator("goal")
    @classmethod
    def _goal_must_not_be_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("goal must not be empty")
        return stripped

    @field_validator("steps")
    @classmethod
    def _steps_must_not_be_empty(cls, v: list[AgentStep]) -> list[AgentStep]:
        if not v:
            raise ValueError("plan must have at least one step")
        return v

    @model_validator(mode="after")
    def _no_duplicate_step_ids(self) -> AgentPlan:
        ids = [s.step_id for s in self.steps]
        if len(ids) != len(set(ids)):
            seen = set()
            dupes = {i for i in ids if i in seen or seen.add(i)}
            raise ValueError(f"duplicate step_id(s): {sorted(dupes)}")
        return self

    @model_validator(mode="after")
    def _no_duplicate_required_tools(self) -> AgentPlan:
        if len(self.required_tools) != len(set(self.required_tools)):
            seen = set()
            dupes = {t for t in self.required_tools if t in seen or seen.add(t)}
            raise ValueError(f"duplicate required_tool(s): {sorted(dupes)}")
        return self


class AgentRun(BaseModel):
    """Complete record of a single agent run."""

    run_id: str
    raw_ticket_text: str
    plan: AgentPlan | None = None
    skill_id: str | None = None
    events: list[AgentEvent] = Field(default_factory=list)
    ticket_output: dict[str, Any] | None = None
    draft_reply: dict[str, Any] | None = None
    review_decision: dict[str, Any] | None = None
    final_status: AgentRunStatus = AgentRunStatus.CREATED
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None

    @field_validator("run_id", "raw_ticket_text")
    @classmethod
    def _must_not_be_empty(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("value must not be empty")
        return stripped

    @model_validator(mode="after")
    def _completed_at_not_before_started_at(self) -> AgentRun:
        if self.completed_at is not None and self.started_at is not None:
            if self.completed_at < self.started_at:
                raise ValueError("completed_at must not be earlier than started_at")
        return self
