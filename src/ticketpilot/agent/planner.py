"""Deterministic planner for the lightweight TicketPilot agent runtime."""

from __future__ import annotations

from ticketpilot.agent.schemas import AgentPlan, AgentPlanStep, AgentToolName


DEFAULT_AGENT_CONSTRAINTS = [
    "Never treat a draft as a sent message.",
    "Use retrieved evidence before creating a draft.",
    "Route high-risk, low-confidence, unsupported, or no-evidence cases to review.",
    "Record plan, tool calls, review decision, and memory writes for audit.",
]

DEFAULT_SUCCESS_CRITERIA = [
    "The ticket is normalized, classified, risk-assessed, and evidence-searched.",
    "The draft is evidence-grounded or clearly marked as fallback.",
    "Review requirement and reasons are explicit.",
    "Tool calls and trace events are available for replay.",
]


def build_ticket_resolution_plan() -> AgentPlan:
    """Build the fixed MVP plan for resolving one support ticket.

    The planner is intentionally deterministic. It turns the TicketPilot workflow into
    an auditable execution plan without introducing autonomous multi-agent behavior.
    """
    return AgentPlan(
        goal="Create an evidence-grounded support draft with explicit review gating.",
        constraints=list(DEFAULT_AGENT_CONSTRAINTS),
        steps=[
            AgentPlanStep(
                step_id="s1",
                title="Process ticket through intake, classification, risk, and retrieval",
                tool_name=AgentToolName.RUN_TICKET_PIPELINE,
                purpose="Create the canonical TicketOutput used by downstream steps.",
                expected_output="TicketOutput with classification, risk assessment, evidence candidates, and retrieval trace.",
            ),
            AgentPlanStep(
                step_id="s2",
                title="Select runtime skill for the classified ticket",
                tool_name=AgentToolName.REVIEW_GATE,
                purpose="Bind the run to a reusable business workflow and review constraints.",
                expected_output="RuntimeSkill with constraints and review triggers.",
            ),
            AgentPlanStep(
                step_id="s3",
                title="Generate evidence-grounded draft",
                tool_name=AgentToolName.GENERATE_DRAFT_REPLY,
                purpose="Produce a draft with citations, confidence, and unsupported-claim checks.",
                expected_output="DraftReply with citations, confidence, fallback reason, and review flag.",
            ),
            AgentPlanStep(
                step_id="s4",
                title="Apply final review gate",
                tool_name=AgentToolName.REVIEW_GATE,
                purpose="Decide whether the run must be escalated for review.",
                expected_output="Review decision and review reasons.",
            ),
            AgentPlanStep(
                step_id="s5",
                title="Write bounded episodic memory if useful",
                tool_name=AgentToolName.WRITE_MEMORY,
                purpose="Persist only run metadata that helps future audits and failure review.",
                expected_output="Memory snapshot with working context and bounded episodic write.",
                required=False,
            ),
        ],
        success_criteria=list(DEFAULT_SUCCESS_CRITERIA),
    )
