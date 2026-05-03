"""TicketPilot Agent Kernel — lightweight agentic workflow runtime.

Batch 1: agent schemas and trace event models.
Batch 2: tool registry and wrapper functions.
Batch 3: deterministic planner, memory, and agent loop.
"""

from ticketpilot.agent.loop import run_agent_pipeline
from ticketpilot.agent.memory import EpisodicMemory, WorkingMemory
from ticketpilot.agent.planner import DeterministicTaskPlanner
from ticketpilot.agent.registry import RegisteredTool, ToolRegistry
from ticketpilot.agent.schemas import (
    AgentEvent,
    AgentEventType,
    AgentPlan,
    AgentRun,
    AgentRunStatus,
    AgentStep,
    AgentToolSpec,
)
from ticketpilot.agent.tools import (
    assess_risk_tool,
    classify_ticket_tool,
    create_default_tool_registry,
    generate_draft_tool,
    normalize_ticket_tool,
    retrieve_evidence_tool,
)
from ticketpilot.agent.trace import AgentTrace

__all__ = [
    # Batch 1 — schemas
    "AgentEventType",
    "AgentEvent",
    "AgentToolSpec",
    "AgentStep",
    "AgentPlan",
    "AgentRunStatus",
    "AgentRun",
    "AgentTrace",
    # Batch 2 — registry and tools
    "RegisteredTool",
    "ToolRegistry",
    "normalize_ticket_tool",
    "classify_ticket_tool",
    "assess_risk_tool",
    "retrieve_evidence_tool",
    "generate_draft_tool",
    "create_default_tool_registry",
    # Batch 3 — planner, memory, loop
    "DeterministicTaskPlanner",
    "WorkingMemory",
    "EpisodicMemory",
    "run_agent_pipeline",
]
