"""Runtime skill selection for TicketPilot agent runs."""

from __future__ import annotations

from ticketpilot.agent.schemas import AgentToolName, RuntimeSkill
from ticketpilot.schema.ticket import IntentClass, RiskFlag, RiskSeverity, TicketOutput

GENERAL_SUPPORT_SKILL = RuntimeSkill(
    name="general_support",
    display_name="General Support Handling",
    when_to_use=["default fallback for unrecognized or mixed tickets"],
    required_tools=[
        AgentToolName.RUN_TICKET_PIPELINE,
        AgentToolName.GENERATE_DRAFT_REPLY,
        AgentToolName.REVIEW_GATE,
    ],
    business_constraints=[
        "Do not invent policy details that are not present in retrieved evidence.",
        "Use fallback wording when evidence is missing.",
    ],
    human_review_triggers=[
        "high severity",
        "insufficient evidence",
        "unsupported claims",
        "fallback draft",
    ],
    source_path="skills/runtime/general_support/SKILL.md",
)

REFUND_REQUEST_SKILL = RuntimeSkill(
    name="refund_request",
    display_name="Refund Request Handling",
    when_to_use=["refund request", "return or exchange request", "refund policy question"],
    required_tools=[
        AgentToolName.RUN_TICKET_PIPELINE,
        AgentToolName.GENERATE_DRAFT_REPLY,
        AgentToolName.REVIEW_GATE,
    ],
    business_constraints=[
        "Do not promise a refund unless evidence supports the condition.",
        "Prefer policy evidence over generic FAQ evidence when available.",
        "Escalate compensation requests and policy conflicts.",
    ],
    human_review_triggers=[
        "compensation risk",
        "policy conflict",
        "legal risk",
        "insufficient evidence",
        "fallback draft",
    ],
    source_path="skills/runtime/refund_request/SKILL.md",
)

COMPLAINT_ESCALATION_SKILL = RuntimeSkill(
    name="complaint_escalation",
    display_name="Complaint and Escalation Handling",
    when_to_use=["complaint", "legal threat", "privacy complaint", "compensation demand"],
    required_tools=[
        AgentToolName.RUN_TICKET_PIPELINE,
        AgentToolName.GENERATE_DRAFT_REPLY,
        AgentToolName.REVIEW_GATE,
    ],
    business_constraints=[
        "Keep the draft factual and evidence-bound.",
        "Do not make liability, legal, or compensation commitments.",
        "Route legal, privacy, or high severity cases to review.",
    ],
    human_review_triggers=[
        "complaint risk",
        "legal risk",
        "privacy risk",
        "compensation risk",
        "high severity",
    ],
    source_path="skills/runtime/complaint_escalation/SKILL.md",
)

ACCOUNT_ISSUE_SKILL = RuntimeSkill(
    name="account_issue",
    display_name="Account Issue Handling",
    when_to_use=["account abnormality", "login issue", "account security issue"],
    required_tools=[
        AgentToolName.RUN_TICKET_PIPELINE,
        AgentToolName.GENERATE_DRAFT_REPLY,
        AgentToolName.REVIEW_GATE,
    ],
    business_constraints=[
        "Do not request sensitive personal information in the draft.",
        "Escalate account security and privacy cases.",
    ],
    human_review_triggers=[
        "account security risk",
        "privacy risk",
        "insufficient evidence",
    ],
    source_path="skills/runtime/account_issue/SKILL.md",
)


def select_skill(ticket_output: TicketOutput | None) -> RuntimeSkill:
    """Select a reusable runtime skill from the processed ticket state."""
    if ticket_output is None:
        return GENERAL_SUPPORT_SKILL

    flags = ticket_output.risk_assessment.flags
    severity = ticket_output.risk_assessment.severity
    intent = ticket_output.classification.intent

    complaint_flags = {
        RiskFlag.COMPLAINT_RISK,
        RiskFlag.LEGAL_RISK,
        RiskFlag.PRIVACY_RISK,
        RiskFlag.COMPENSATION_RISK,
    }
    if severity == RiskSeverity.HIGH or flags.intersection(complaint_flags):
        return COMPLAINT_ESCALATION_SKILL

    if intent in {IntentClass.REFUND, IntentClass.RETURN_EXCHANGE}:
        return REFUND_REQUEST_SKILL

    if intent == IntentClass.ACCOUNT_ISSUE or RiskFlag.ACCOUNT_SECURITY_RISK in flags:
        return ACCOUNT_ISSUE_SKILL

    return GENERAL_SUPPORT_SKILL
