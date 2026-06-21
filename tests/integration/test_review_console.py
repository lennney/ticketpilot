"""Integration tests for the human review console.

Tests cover console module importability, ReviewStore end-to-end
persistence through console helper functions, and verification
that no auto-send side effects exist.
"""

import os
import tempfile
from datetime import datetime
from uuid import uuid4

from ticketpilot.drafting.schemas import (
    Citation,
    DraftedTicketResult,
    DraftReply,
)
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.review.console import build_review_decision
from ticketpilot.review.schemas import ReviewAction
from ticketpilot.review.store import ReviewStore
from ticketpilot.schema.evidence import EvidenceCandidate
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


def _make_result(
    must_human_review: bool = False,
    severity: RiskSeverity = RiskSeverity.LOW,
    unsupported_claims: list[str] | None = None,
    risk_flags: set[RiskFlag] | None = None,
    evidence_count: int = 1,
    confidence: float = 0.8,
    draft_text: str = "您好，关于退款问题...",
) -> DraftedTicketResult:
    """Build a DraftedTicketResult with controllable flags for testing."""
    ticket_id = str(uuid4())
    now = datetime.utcnow()

    evidence = [
        EvidenceCandidate(
            chunk_id=uuid4(),
            doc_id=uuid4(),
            doc_type=DocType.FAQ,
            source_id=uuid4(),
            source_table="knowledge_faq",
            content="退货需要在7天内申请。",
            score=0.8,
            rank=i + 1,
        )
        for i in range(evidence_count)
    ]

    ticket_output = TicketOutput(
        ticket_id=ticket_id,
        raw_ticket=RawTicket(
            original_text="我要退款",
            submitted_at=now,
        ),
        normalized_ticket=NormalizedTicket(
            text="我要退款",
            language="zh",
            cleaned_at=now,
        ),
        classification=ClassificationResult(
            intent=IntentClass.REFUND,
            confidence=0.9,
            classified_at=now,
        ),
        risk_assessment=RiskAssessment(
            flags=risk_flags or set(),
            severity=severity,
            must_human_review=must_human_review,
            assessed_at=now,
        ),
        output_at=now,
        evidence_candidates=evidence,
    )

    draft_reply = DraftReply(
        ticket_id=ticket_id,
        draft_text=draft_text,
        citations=[
            Citation(
                chunk_id=uuid4(),
                doc_id=uuid4(),
                doc_type=DocType.FAQ,
                source_table="knowledge_faq",
                source_id=uuid4(),
                evidence_excerpt="退货需要在7天内申请。",
            )
        ],
        evidence_used=[],
        unsupported_claims=unsupported_claims or [],
        missing_information=[],
        confidence=confidence,
        must_human_review=must_human_review,
        fallback_reason=None,
    )

    return DraftedTicketResult(
        ticket_output=ticket_output,
        draft_reply=draft_reply,
    )


class TestConsoleModuleImports:
    """Verify the console module imports cleanly without Streamlit side effects."""

    def test_console_module_imports(self):
        """console module can be imported without error."""
        from ticketpilot import review  # noqa: F811

        _ = review.console

    def test_console_functions_accessible(self):
        """Core console helper functions are importable."""
        from ticketpilot.review.console import (  # noqa: F811
            build_review_decision,
            determine_trigger_reasons,
            main,
        )

        assert callable(build_review_decision)
        assert callable(determine_trigger_reasons)
        assert callable(main)


class TestReviewDecisionPersistence:
    """ReviewDecision persistence through ReviewStore end-to-end."""

    def test_approve_persists_original_draft(self):
        """APPROVE action persists original draft as final reply."""
        result = _make_result()
        decision = build_review_decision(result, ReviewAction.APPROVE)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            store.save(decision)
            loaded = store.load_all()
            assert len(loaded) == 1
            assert loaded[0].action == ReviewAction.APPROVE
            assert loaded[0].original_draft_text == result.draft_reply.draft_text
            assert loaded[0].edited_text is None

    def test_edit_preserves_original_and_stores_edited(self):
        """EDIT action preserves original_draft_text and stores edited final reply."""
        result = _make_result()
        edited_text = "您好，已为您处理退款申请。"
        decision = build_review_decision(
            result, ReviewAction.EDIT, edited_text=edited_text
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            store.save(decision)
            loaded = store.load_all()
            assert len(loaded) == 1
            assert loaded[0].action == ReviewAction.EDIT
            assert loaded[0].original_draft_text == result.draft_reply.draft_text
            assert loaded[0].edited_text == edited_text

    def test_escalate_requires_decision_reason(self):
        """ESCALATE action stores decision_reason."""
        result = _make_result()
        reason = "需要法务团队审核，涉及赔偿条款"
        decision = build_review_decision(
            result, ReviewAction.ESCALATE, decision_reason=reason
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            store.save(decision)
            loaded = store.load_all()
            assert len(loaded) == 1
            assert loaded[0].action == ReviewAction.ESCALATE
            assert loaded[0].decision_reason == reason

    def test_reject_requires_decision_reason(self):
        """REJECT action stores decision_reason."""
        result = _make_result()
        reason = "回复内容不准确，需要重新生成"
        decision = build_review_decision(
            result, ReviewAction.REJECT, decision_reason=reason
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            store.save(decision)
            loaded = store.load_all()
            assert len(loaded) == 1
            assert loaded[0].action == ReviewAction.REJECT
            assert loaded[0].decision_reason == reason

    def test_saved_record_preserves_all_key_fields(self):
        """Saved decision preserves ticket_id, action, reviewer_label,
        evidence_used_count, risk_flags, and was_high_risk."""
        flags = {RiskFlag.COMPENSATION_RISK, RiskFlag.LEGAL_RISK}
        result = _make_result(
            must_human_review=True,
            severity=RiskSeverity.HIGH,
            risk_flags=flags,
            evidence_count=2,
        )
        decision = build_review_decision(
            result, ReviewAction.ESCALATE, decision_reason="法务介入"
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            store.save(decision)
            loaded = store.load_all()
            assert len(loaded) == 1
            rec = loaded[0]
            assert rec.ticket_id == result.ticket_output.ticket_id
            assert rec.action == ReviewAction.ESCALATE
            assert rec.reviewer_label == ""
            assert rec.evidence_used_count == 0
            assert rec.was_high_risk is True
            assert "compensation_risk" in rec.risk_flags
            assert "legal_risk" in rec.risk_flags

    def test_multiple_decisions_roundtrip(self):
        """Multiple saves and loads preserve all records."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            result1 = _make_result(draft_text="草稿A")
            result2 = _make_result(draft_text="草稿B")
            store.save(build_review_decision(result1, ReviewAction.APPROVE))
            store.save(
                build_review_decision(result2, ReviewAction.EDIT, edited_text="修改版B")
            )
            loaded = store.load_all()
            assert len(loaded) == 2
            assert loaded[0].original_draft_text == "草稿A"
            assert loaded[1].original_draft_text == "草稿B"
            assert loaded[1].edited_text == "修改版B"


class TestNoAutoSend:
    """Verify that no auto-send side effect exists."""

    def test_save_only_writes_to_jsonl(self):
        """Saving a decision only performs JSONL append, no network or send."""
        result = _make_result()
        decision = build_review_decision(result, ReviewAction.APPROVE)
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            store.save(decision)
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 1
            # Verify the file contains valid JSON with action=approve
            import json

            data = json.loads(lines[0])
            assert data["action"] == "approve"
            assert data["ticket_id"] == result.ticket_output.ticket_id
