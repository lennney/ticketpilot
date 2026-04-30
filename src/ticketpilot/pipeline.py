"""End-to-end intake-risk pipeline for ticket processing."""

import uuid
from datetime import datetime

from ticketpilot.schema.ticket import (
    ClassificationResult,
    IntentClass,
    NormalizedTicket,
    RawTicket,
    RiskAssessment,
    RiskFlag,
    RiskSeverity,
    TicketOutput,
)
from ticketpilot.intake.pipeline import pipeline as intake_pipeline
from ticketpilot.classification.classifier import IntentClassifier
from ticketpilot.risk.assessor import RiskAssessor
from ticketpilot.retrieval.retrieve_evidence import retrieve_evidence


class PipelineError(Exception):
    """Error during pipeline processing."""

    pass


def _with_added_risk_flag(assessment: RiskAssessment, flag: RiskFlag) -> RiskAssessment:
    """Return a new RiskAssessment with *flag* added, without mutating the original."""
    new_flags = assessment.flags | {flag}
    return RiskAssessment(
        flags=new_flags,
        severity=assessment.severity,
        must_human_review=True,
        assessed_at=assessment.assessed_at,
    )


def intake_risk_pipeline(raw_ticket: RawTicket) -> TicketOutput:
    """
    Process a raw ticket through a 4-stage pipeline:

    1. Intake — normalize and extract entities
    2. Classification — determine intent
    3. Risk assessment — evaluate risk flags and severity
    4. Evidence retrieval — search knowledge base for relevant evidence

    Args:
        raw_ticket: RawTicket to process

    Returns:
        TicketOutput with all processing stages completed
    """
    try:
        # Stage 1: Intake - normalize and extract entities
        normalized_ticket = intake_pipeline(raw_ticket)
    except Exception:
        # Graceful degradation for intake errors
        normalized_ticket = NormalizedTicket(
            text="",
            language="unknown",
            order_numbers=[],
            product_info=None,
            amount=None,
            cleaned_at=datetime.utcnow(),
        )

    try:
        # Stage 2: Classification - determine intent
        classifier = IntentClassifier()
        classification = classifier.classify(normalized_ticket.text)
    except Exception:
        # Graceful degradation for classification errors
        classification = ClassificationResult(
            intent=IntentClass.OTHER,
            confidence=0.5,
            classified_at=datetime.utcnow(),
        )

    try:
        # Stage 3: Risk assessment - evaluate risk flags and severity
        assessor = RiskAssessor()
        risk_assessment = assessor.assess(normalized_ticket, classification)
    except Exception:
        # Graceful degradation for risk assessment errors
        risk_assessment = RiskAssessment(
            flags={RiskFlag.LOW_CONFIDENCE},
            severity=RiskSeverity.LOW,
            must_human_review=True,
            assessed_at=datetime.utcnow(),
        )

    # Stage 4: Evidence retrieval
    try:
        candidates, trace = retrieve_evidence(
            normalized_text=normalized_ticket.text,
            intent=classification.intent,
            risk_flags=risk_assessment.flags,
        )
    except Exception:
        candidates = []
        trace = None

    if not candidates:
        risk_assessment = _with_added_risk_flag(
            risk_assessment, RiskFlag.INSUFFICIENT_EVIDENCE
        )

    return TicketOutput(
        ticket_id=str(uuid.uuid4()),
        raw_ticket=raw_ticket,
        normalized_ticket=normalized_ticket,
        classification=classification,
        risk_assessment=risk_assessment,
        output_at=datetime.utcnow(),
        evidence_candidates=candidates,
        retrieval_trace=trace,
    )
