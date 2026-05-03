"""Pydantic schemas for the lightweight TicketPilot agent runtime."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.schema.ticket import TicketOutput


class AgentStepStatus(str, Enum):
    """Execution status for a planned agent step."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class AgentToolName(str, Enum):
    """Stable tool names exposed to the agent runtime."""

    RUN_TICKET_PIPELINE = "run_ticket_pipeline"
    GENERATE_DRAFT_REPLY = "generate_draft_reply"
    REVIEW_GATE = "review_gate"
    WRITE_MEMORY = "write_memory"


class AgentTraceEventType(str, Enum):
    """Run-level trace event types."""

    RUN_STARTED = "run_started"
    PLAN_CREATED = "plan_created"
    SKILL_SELECTED = "skill_selected"
    TOOL_CALLED = "tool_called"
    TOOL_RETURNED = "tool_returned"
    TOOL_FAILED = "tool_failed"
    MEMORY_WRITTEN = "memory_written"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"


class AgentPlanStep(BaseModel):
    """One deterministic step in the ticket-resolution plan."""

    step_id: str
    title: str
    tool_name: AgentToolName
    purpose: str
    expected_output: str
    required: bool = True
    status: AgentStepStatus = AgentStepStatus.PENDING


class AgentPlan(BaseModel):
    """Structured task plan produced before tool execution."""

    goal: str
    constraints: list[str]
    steps: list[AgentPlanStep]
    success_criteria: list[str]
    created_at: datetime = Field(default_factory=datetime.utcnow)


class RuntimeSkill(BaseModel):
    """Reusable business workflow selected for a ticket."""

    name: str
    display_name: str
    when_to_use: list[str] = Field(default_factory=list)
    required_tools: list[AgentToolName] = Field(default_factory=list)
    business_constraints: list[str] = Field(default_factory=list)
    human_review_triggers: list[str] = Field(default_factory=list)
    source_path: str | None = None


class ToolCallRecord(BaseModel):
    """Audit record for one tool call."""

    tool_name: AgentToolName
    status: AgentStepStatus
    input_summary: str
    output_summary: str
    latency_ms: float
    error: str | None = None
    called_at: datetime = Field(default_factory=datetime.utcnow)


class ToolExecutionResult(BaseModel):
    """Tool output plus its normalized audit record."""

    output: dict[str, Any]
    record: ToolCallRecord


class AgentTraceEvent(BaseModel):
    """One event in an agent run trace."""

    event_type: AgentTraceEventType
    summary: str
    step_id: str | None = None
    tool_name: AgentToolName | None = None
    status: AgentStepStatus | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AgentMemorySnapshot(BaseModel):
    """Serializable snapshot of runtime memory after a run."""

    working: dict[str, Any] = Field(default_factory=dict)
    episodic_writes: list[dict[str, Any]] = Field(default_factory=list)


class AgentRunResult(BaseModel):
    """Complete result returned by the TicketPilot agent runtime."""

    run_id: str
    plan: AgentPlan
    selected_skill: RuntimeSkill
    ticket_output: TicketOutput | None = None
    draft_reply: DraftReply | None = None
    human_review_required: bool = False
    review_reasons: list[str] = Field(default_factory=list)
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    trace_events: list[AgentTraceEvent] = Field(default_factory=list)
    memory_snapshot: AgentMemorySnapshot = Field(default_factory=AgentMemorySnapshot)
    completed_at: datetime = Field(default_factory=datetime.utcnow)
