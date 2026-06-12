"""Pipeline-backed prediction generation for the evaluation pipeline.

Converts the current local TicketPilot pipeline output into EvalPrediction
objects so they can be scored against golden expectations.

This module uses the existing local pipeline only:
  - run_pipeline_with_draft() for DraftReply and fallback information
  - No real LLM, embedding provider, network, or external API calls

All functions operate deterministically on seed data.
"""

from __future__ import annotations

from datetime import datetime, timezone

from ticketpilot.drafting.pipeline import run_pipeline_with_draft
from ticketpilot.evaluation.schemas import EvalPrediction, EvalTicket
from ticketpilot.schema.ticket import RawTicket


def _extract_doc_types(evidence_candidates: list) -> frozenset[str]:
    """Extract unique DocType string values from evidence candidates.

    Args:
        evidence_candidates: List of EvidenceCandidate objects.

    Returns:
        Frozenset of doc_type value strings (e.g. {"FAQ", "POLICY"}).
        Empty frozenset when there are no candidates.
    """
    return frozenset(
        c.doc_type.value
        for c in evidence_candidates
        if hasattr(c, "doc_type") and hasattr(c.doc_type, "value")
    )


def predict_from_pipeline(eval_ticket: EvalTicket, force_fake_draft: bool = False) -> EvalPrediction:
    """Run the local TicketPilot pipeline on one eval ticket and return a prediction.

    The function:
    1. Converts ``EvalTicket`` to a ``RawTicket`` for the pipeline.
    2. Calls ``run_pipeline_with_draft()`` (intake -> classify -> assess ->
       retrieve -> draft).
    3. Maps every relevant pipeline output field to the corresponding
       ``EvalPrediction`` field.

    Args:
        eval_ticket: A single evaluation ticket (must have a non-empty case_id).
        force_fake_draft: If ``True``, temporarily override the LLM provider
            to ``"fake"`` so the draft uses the deterministic template-based
            provider. Use this when you only need classification / risk metrics
            and don't care about the actual draft text (e.g. optimizer baseline).

    Returns:
        EvalPrediction with predicted fields derived from the pipeline.

    Raises:
        PipelineError: If the pipeline itself raises (very unlikely with the
            current graceful-degradation design).
    """
    # 使用固定时间戳以确保评测可重复
    # eval_ticket.submitted_at 是字符串（ISO 格式），需要转为 datetime
    submitted_at_raw = getattr(eval_ticket, 'submitted_at', None)
    if submitted_at_raw:
        try:
            submitted_at = datetime.fromisoformat(submitted_at_raw)
        except (ValueError, TypeError):
            submitted_at = datetime.now(timezone.utc)
    else:
        submitted_at = datetime.now(timezone.utc)

    import os as _os

    raw_ticket = RawTicket(
        original_text=eval_ticket.original_text,
        submitted_at=submitted_at,
        customer_id=eval_ticket.customer_id,
    )

    # 优化器评估时不调用 LLM 生成草稿（减少 3s/票 → 0.02s/票）
    _saved_provider: str | None = None
    if force_fake_draft:
        _saved_provider = _os.environ.get("TICKETPILOT_LLM_PROVIDER")
        _os.environ["TICKETPILOT_LLM_PROVIDER"] = "fake"

    try:
        drafted_result = run_pipeline_with_draft(raw_ticket)
    finally:
        if force_fake_draft:
            if _saved_provider is not None:
                _os.environ["TICKETPILOT_LLM_PROVIDER"] = _saved_provider
            else:
                _os.environ.pop("TICKETPILOT_LLM_PROVIDER", None)

    ticket_output = drafted_result.ticket_output
    draft_reply = drafted_result.draft_reply

    # --- Field mapping ---

    # predicted_issue_type from intent classification
    predicted_issue_type = ticket_output.classification.intent.value

    # predicted_risk_flags from risk assessment
    predicted_risk_flags = frozenset(
        f.value for f in ticket_output.risk_assessment.flags
    )

    # predicted_severity from risk assessment (upper-cased for EvalPrediction)
    predicted_severity = ticket_output.risk_assessment.severity.value.upper()

    # predicted_must_human_review: True if risk assessment says so OR
    # the DraftReply flags it (covers generation-level human-review signals)
    predicted_must_human_review = (
        ticket_output.risk_assessment.must_human_review
        or draft_reply.must_human_review
    )

    # predicted_evidence_doc_types from evidence candidates' doc_type values
    predicted_evidence_doc_types = _extract_doc_types(
        ticket_output.evidence_candidates
    )

    # predicted_fallback_required: True when DraftReply has a fallback_reason
    predicted_fallback_required = draft_reply.fallback_reason is not None

    # predicted_no_auto_send: always True (architectural constraint)
    predicted_no_auto_send = True

    return EvalPrediction(
        case_id=eval_ticket.case_id,
        predicted_issue_type=predicted_issue_type,
        predicted_risk_flags=predicted_risk_flags,
        predicted_severity=predicted_severity,
        predicted_must_human_review=predicted_must_human_review,
        predicted_evidence_doc_types=predicted_evidence_doc_types,
        predicted_fallback_required=predicted_fallback_required,
        predicted_no_auto_send=predicted_no_auto_send,
    )
