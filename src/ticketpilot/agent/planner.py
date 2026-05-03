"""Deterministic task planner — converts ticket text to an AgentPlan.

No LLM, no tools, no pipeline calls. Only keyword matching.
"""

from __future__ import annotations

from ticketpilot.agent.schemas import AgentPlan, AgentStep


def _contains(text: str, keywords: list[str]) -> bool:
    lowered = text.lower()
    return any(kw.lower() in lowered for kw in keywords)


_TEMPLATES: list[tuple[str, str, list[str]]] = [
    (
        "complaint_escalation",
        "Handle complaint or legal-risk ticket with escalation steps",
        ["投诉", "举报", "法律", "起诉", "赔偿", "compensation", "complaint"],
    ),
    (
        "refund_request",
        "Process a refund request ticket",
        ["退款", "退钱", "退费", "refund"],
    ),
    (
        "return_exchange",
        "Handle return or exchange request",
        ["换货", "退货", "退换", "return", "exchange"],
    ),
    (
        "account_issue",
        "Resolve account or login issue",
        ["账号", "登录", "密码", "账户", "安全", "login", "account"],
    ),
    (
        "logistics_query",
        "Respond to logistics or delivery inquiry",
        ["物流", "快递", "没收到", "配送", "delivery", "shipping"],
    ),
    (
        "technical_issue",
        "Diagnose and resolve technical issue",
        ["故障", "报错", "不能用", "崩溃", "bug", "error"],
    ),
]

_TEMPLATE_GOALS: dict[str, str] = {
    "complaint_escalation": "Handle complaint or legal-risk ticket with escalation steps",
    "refund_request": "Process a refund request ticket",
    "return_exchange": "Handle return or exchange request",
    "account_issue": "Resolve account or login issue",
    "logistics_query": "Respond to logistics or delivery inquiry",
    "technical_issue": "Diagnose and resolve technical issue",
    "generic_support": "Provide general support for the ticket",
}

_TEMPLATE_CONSTRAINTS: dict[str, list[str]] = {
    "complaint_escalation": [
        "No auto-send",
        "Use evidence-grounded draft only",
        "Human review required for high-risk or unsupported outputs",
        "Escalate to human reviewer for all complaint and legal-risk tickets",
    ],
}

_GENERIC_CONSTRAINTS = [
    "No auto-send",
    "Use evidence-grounded draft only",
    "Human review required for high-risk or unsupported outputs",
]

_TEMPLATE_SUCCESS: dict[str, list[str]] = {
    "complaint_escalation": [
        "Ticket normalized and classified",
        "Risk assessed with complaint/legal flags",
        "Evidence retrieved for escalation",
        "Draft generated with escalation note",
    ],
    "refund_request": [
        "Ticket normalized and classified as refund",
        "Risk assessed for refund request",
        "Evidence retrieved for refund policy",
        "Draft generated with refund options",
    ],
    "return_exchange": [
        "Ticket normalized and classified as return/exchange",
        "Risk assessed",
        "Evidence retrieved for return/exchange policy",
        "Draft generated with return/exchange instructions",
    ],
    "account_issue": [
        "Ticket normalized and classified as account issue",
        "Risk assessed for account security",
        "Evidence retrieved for account recovery procedures",
        "Draft generated with account troubleshooting steps",
    ],
    "logistics_query": [
        "Ticket normalized and classified as logistics query",
        "Risk assessed",
        "Evidence retrieved for logistics/delivery information",
        "Draft generated with delivery status update",
    ],
    "technical_issue": [
        "Ticket normalized and classified as technical issue",
        "Risk assessed",
        "Evidence retrieved for relevant technical documentation",
        "Draft generated with troubleshooting steps",
    ],
    "generic_support": [
        "Ticket normalized and classified",
        "Risk assessed",
        "Evidence retrieved if relevant",
        "Draft generated with general support information",
    ],
}

# Shared 5-step plan used by all templates
_CORE_STEPS: list[AgentStep] = [
    AgentStep(
        step_id="s1_normalize",
        description="Normalize raw ticket text and extract entities",
        tool_name="normalize_ticket",
        expected_output="NormalizedTicket dict",
    ),
    AgentStep(
        step_id="s2_classify",
        description="Classify ticket intent from normalized text",
        tool_name="classify_ticket",
        expected_output="ClassificationResult dict",
    ),
    AgentStep(
        step_id="s3_assess_risk",
        description="Assess risk flags and severity for the ticket",
        tool_name="assess_risk",
        expected_output="RiskAssessment dict",
    ),
    AgentStep(
        step_id="s4_retrieve_evidence",
        description="Retrieve evidence candidates from the knowledge base",
        tool_name="retrieve_evidence",
        expected_output="Evidence list with retrieval trace",
    ),
    AgentStep(
        step_id="s5_generate_draft",
        description="Generate evidence-grounded draft reply",
        tool_name="generate_draft",
        expected_output="DraftReply dict",
    ),
]

_REQUIRED_TOOLS = [
    "normalize_ticket",
    "classify_ticket",
    "assess_risk",
    "retrieve_evidence",
    "generate_draft",
]


class DeterministicTaskPlanner:
    """Converts raw ticket text into a deterministic AgentPlan."""

    def select_template(self, text: str) -> str:
        """Select a template id based on keyword matching.

        Returns one of: complaint_escalation, refund_request, return_exchange,
        account_issue, logistics_query, technical_issue, generic_support.
        """
        if not text or not text.strip():
            return "generic_support"

        for template_id, _goal, keywords in _TEMPLATES:
            if _contains(text, keywords):
                return template_id

        return "generic_support"

    def create_plan(self, text: str) -> AgentPlan:
        """Create a deterministic AgentPlan from ticket text."""
        if not text or not text.strip():
            raise ValueError("ticket text must not be empty")

        template_id = self.select_template(text)
        goal = _TEMPLATE_GOALS[template_id]
        constraints = _TEMPLATE_CONSTRAINTS.get(template_id, _GENERIC_CONSTRAINTS)
        success_criteria = _TEMPLATE_SUCCESS.get(
            template_id, _TEMPLATE_SUCCESS["generic_support"]
        )

        return AgentPlan(
            goal=goal,
            constraints=constraints,
            steps=_CORE_STEPS.copy(),
            required_tools=_REQUIRED_TOOLS.copy(),
            success_criteria=success_criteria,
        )
