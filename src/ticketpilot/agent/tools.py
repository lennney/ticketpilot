"""Agent tool wrappers around existing TicketPilot capabilities.

Each function is a thin adapter — it converts dict input to the
required Pydantic models, calls existing pipeline logic, and returns
dict output. No existing module is modified.
"""

from __future__ import annotations

from typing import Any

from ticketpilot.agent.registry import RegisteredTool, ToolRegistry
from ticketpilot.agent.schemas import AgentToolSpec
from ticketpilot.classification.classifier import IntentClassifier
from ticketpilot.risk.assessor import RiskAssessor
from ticketpilot.drafting.generate import generate_draft
from ticketpilot.intake.pipeline import pipeline as intake_pipeline
from ticketpilot.retrieval.retrieve_evidence import retrieve_evidence
from ticketpilot.schema.ticket import (
    ClassificationResult,
    IntentClass,
    NormalizedTicket,
    RawTicket,
    RiskFlag,
    TicketOutput,
)


def normalize_ticket_tool(input_data: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw ticket via the intake pipeline.

    Input:
        raw_ticket: RawTicket instance or equivalent dict
    """
    raw = input_data["raw_ticket"]
    if isinstance(raw, dict):
        raw = RawTicket(**raw)
    result = intake_pipeline(raw)
    return result.model_dump(mode="json")


def classify_ticket_tool(input_data: dict[str, Any]) -> dict[str, Any]:
    """Classify ticket intent from normalized text.

    Input:
        normalized_text: str
    """
    text = input_data["normalized_text"]
    classifier = IntentClassifier()
    result = classifier.classify(text)
    return result.model_dump(mode="json")


def assess_risk_tool(input_data: dict[str, Any]) -> dict[str, Any]:
    """Assess risk flags and severity for a normalized ticket.

    Input:
        normalized_ticket: NormalizedTicket instance or equivalent dict
        classification: ClassificationResult instance or equivalent dict
    """
    nt = input_data["normalized_ticket"]
    if isinstance(nt, dict):
        nt = NormalizedTicket(**nt)

    cl = input_data["classification"]
    if isinstance(cl, dict):
        cl = ClassificationResult(**cl)

    assessor = RiskAssessor()
    result = assessor.assess(nt, cl)
    return result.model_dump(mode="json")


def _parse_intent(raw: Any) -> IntentClass:
    if isinstance(raw, IntentClass):
        return raw
    if isinstance(raw, str):
        try:
            return IntentClass(raw)
        except ValueError:
            valid = [e.value for e in IntentClass]
            raise ValueError(f"invalid intent '{raw}'; valid values: {valid}") from None
    raise TypeError(f"unexpected intent type: {type(raw).__name__}")


def _parse_risk_flags(raw: Any) -> set[RiskFlag]:
    if isinstance(raw, set):
        if all(isinstance(f, RiskFlag) for f in raw):
            return raw
        return {_parse_single_risk_flag(f) for f in raw}
    if isinstance(raw, list):
        return {_parse_single_risk_flag(f) for f in raw}
    raise TypeError(f"unexpected risk_flags type: {type(raw).__name__}")


def _parse_single_risk_flag(raw: Any) -> RiskFlag:
    if isinstance(raw, RiskFlag):
        return raw
    if isinstance(raw, str):
        try:
            return RiskFlag(raw)
        except ValueError:
            valid = [e.value for e in RiskFlag]
            raise ValueError(
                f"invalid risk_flag '{raw}'; valid values: {valid}"
            ) from None
    raise TypeError(f"unexpected risk_flag type: {type(raw).__name__}")


def retrieve_evidence_tool(input_data: dict[str, Any]) -> dict[str, Any]:
    """Retrieve evidence candidates from the knowledge base.

    Input:
        normalized_text: str
        intent: IntentClass or str
        risk_flags: set[RiskFlag] or list[str/RiskFlag]
        top_k: int (optional, default 10)
    """
    import logging

    normalized_text = input_data["normalized_text"]
    intent = _parse_intent(input_data["intent"])
    risk_flags = _parse_risk_flags(input_data["risk_flags"])
    top_k = input_data.get("top_k", 10)

    try:
        candidates, trace = retrieve_evidence(
            normalized_text=normalized_text,
            intent=intent,
            risk_flags=risk_flags,
            top_k=top_k,
        )
    except Exception as exc:
        logging.warning("Evidence retrieval failed, returning empty results: %s", exc)
        candidates, trace = [], None

    # RetrievalTrace is a Pydantic model; it serialises cleanly via model_dump.
    return {
        "evidence_candidates": [c.model_dump(mode="json") for c in candidates],
        "retrieval_trace": trace.model_dump(mode="json") if trace is not None else None,
        "evidence_count": len(candidates),
    }


def generate_draft_tool(input_data: dict[str, Any]) -> dict[str, Any]:
    """Generate an evidence-grounded draft reply.

    Input:
        ticket_output: TicketOutput instance or equivalent dict
    """
    to = input_data["ticket_output"]
    if isinstance(to, dict):
        to = TicketOutput(**to)
    result = generate_draft(to)
    return result.model_dump(mode="json")


def request_human_input_tool(input_data: dict[str, Any]) -> dict[str, Any]:
    """Request human input for a decision. Pauses the agent run.

    Factor 7: Contact Humans with Tool Calls

    Input:
        question: str — what to ask the human
        context: dict — relevant context for the human
        options: list[str] — optional predefined choices
        urgency: str — "low" | "medium" | "high"

    Output:
        status: "pause_requested"
        question: str
        context: dict
        options: list[str]
        urgency: str
    """
    return {
        "status": "pause_requested",
        "question": input_data["question"],
        "context": input_data.get("context", {}),
        "options": input_data.get("options", []),
        "urgency": input_data.get("urgency", "medium"),
    }


_DEFAULT_TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "normalize_ticket",
        "description": "Normalize raw ticket text and extract entities",
        "input_schema": {
            "type": "object",
            "properties": {
                "raw_ticket": {
                    "oneOf": [
                        {"type": "object"},
                        {"$ref": "#/definitions/RawTicket"},
                    ],
                },
            },
            "required": ["raw_ticket"],
        },
        "output_schema": {"type": "object"},
        "risk_level": "low",
        "handler": normalize_ticket_tool,
    },
    {
        "name": "classify_ticket",
        "description": "Classify ticket intent from normalized text",
        "input_schema": {
            "type": "object",
            "properties": {
                "normalized_text": {"type": "string"},
            },
            "required": ["normalized_text"],
        },
        "output_schema": {"type": "object"},
        "risk_level": "low",
        "handler": classify_ticket_tool,
    },
    {
        "name": "assess_risk",
        "description": "Assess risk flags and severity for a ticket",
        "input_schema": {
            "type": "object",
            "properties": {
                "normalized_ticket": {"type": "object"},
                "classification": {"type": "object"},
            },
            "required": ["normalized_ticket", "classification"],
        },
        "output_schema": {"type": "object"},
        "risk_level": "medium",
        "handler": assess_risk_tool,
    },
    {
        "name": "retrieve_evidence",
        "description": "Retrieve evidence candidates from the knowledge base",
        "input_schema": {
            "type": "object",
            "properties": {
                "normalized_text": {"type": "string"},
                "intent": {"type": "string"},
                "risk_flags": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "top_k": {"type": "integer", "default": 10},
            },
            "required": ["normalized_text", "intent", "risk_flags"],
        },
        "output_schema": {"type": "object"},
        "risk_level": "medium",
        "handler": retrieve_evidence_tool,
    },
    {
        "name": "generate_draft",
        "description": "Generate an evidence-grounded draft reply",
        "input_schema": {
            "type": "object",
            "properties": {
                "ticket_output": {"type": "object"},
            },
            "required": ["ticket_output"],
        },
        "output_schema": {"type": "object"},
        "risk_level": "high",
        "handler": generate_draft_tool,
    },
    {
        "name": "request_human_input",
        "description": "Request human input for a decision. Pauses the agent run until human responds.",
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "What to ask the human"},
                "context": {
                    "type": "object",
                    "description": "Relevant context for the human",
                },
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Predefined choices (optional)",
                },
                "urgency": {
                    "type": "string",
                    "enum": ["low", "medium", "high"],
                    "default": "medium",
                },
            },
            "required": ["question"],
        },
        "output_schema": {"type": "object"},
        "risk_level": "low",
        "handler": request_human_input_tool,
    },
]


def create_default_tool_registry() -> ToolRegistry:
    """Create and populate a ToolRegistry with all 5 default tools."""
    registry = ToolRegistry()
    for d in _DEFAULT_TOOL_DEFS:
        handler = d["handler"]
        spec = AgentToolSpec(
            name=d["name"],
            description=d["description"],
            input_schema=d["input_schema"],
            output_schema=d["output_schema"],
            risk_level=d["risk_level"],
        )
        registry.register(RegisteredTool(spec=spec, handler=handler))
    return registry
