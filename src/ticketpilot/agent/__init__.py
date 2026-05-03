"""TicketPilot Agent Kernel — lightweight agentic workflow runtime.

Batch 1: agent schemas and trace event models only.
Batch 2: tool registry and wrapper functions.
"""

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
]
