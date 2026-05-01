"""Draft provider interface and deterministic FakeDraftProvider."""

from abc import ABC, abstractmethod

from ticketpilot.drafting.schemas import Citation, DraftReply
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import ClassificationResult, RiskAssessment

NO_EVIDENCE_FALLBACK_TEXT = (
    "根据现有信息，无法确认具体政策条款，建议转人工处理。"
)


class AbstractDraftProvider(ABC):
    """Interface for draft generation providers."""

    @abstractmethod
    def generate(
        self,
        evidence_candidates: list[EvidenceCandidate],
        risk_assessment: RiskAssessment,
        classification: ClassificationResult,
        normalized_text: str,
    ) -> DraftReply:
        """Generate a reply draft from evidence and ticket context.

        Args:
            evidence_candidates: Retrieved evidence from the knowledge base.
            risk_assessment: Risk assessment result for the ticket.
            classification: Intent classification result.
            normalized_text: Normalized ticket text.

        Returns:
            DraftReply with citations and guard flags.
        """
        ...


class FakeDraftProvider(AbstractDraftProvider):
    """Deterministic, template-based draft provider for MVP.

    Builds replies from evidence content using simple templates.
    No LLM calls, no network, no API keys.
    """

    def generate(
        self,
        evidence_candidates: list[EvidenceCandidate],
        risk_assessment: RiskAssessment,
        classification: ClassificationResult,
        normalized_text: str,
    ) -> DraftReply:
        # No-evidence fallback
        if not evidence_candidates:
            return DraftReply(
                ticket_id="",
                draft_text=NO_EVIDENCE_FALLBACK_TEXT,
                citations=[],
                evidence_used=[],
                unsupported_claims=[],
                missing_information=["未找到相关证据"],
                confidence=0.0,
                must_human_review=True,
                fallback_reason="no_evidence",
            )

        # Sort by rank ascending
        sorted_evidence = sorted(evidence_candidates, key=lambda e: e.rank)
        top_n = sorted_evidence[:3]

        # Build citations from evidence
        citations: list[Citation] = []
        for ev in top_n:
            citations.append(
                Citation(
                    chunk_id=ev.chunk_id,
                    doc_id=ev.doc_id,
                    doc_type=ev.doc_type,
                    source_table=ev.source_table if hasattr(ev, "source_table") else "",
                    source_id=ev.source_id if hasattr(ev, "source_id") else ev.doc_id,
                    evidence_excerpt=ev.content[:200],
                    claim_supported=True,
                )
            )

        # Build template-based draft text
        intent_label = classification.intent.value if classification else "unknown"
        lines: list[str] = [
            f"您好，关于您反馈的{intent_label}问题，",
        ]
        for i, citation in enumerate(citations, start=1):
            title = getattr(citation, "title", None)
            label = f"（{title}）" if title else ""
            lines.append(
                f"根据相关资料{label}[{i}]，{citation.evidence_excerpt[:100]}。"
            )
        lines.append("")
        lines.append("希望以上信息对您有帮助。如有其他问题，请随时联系我们。")

        draft_text = "\n".join(lines)

        # Compute confidence from average evidence score
        avg_score = (
            sum(e.score for e in top_n) / len(top_n) if top_n else 0.0
        )
        confidence = max(0.0, min(1.0, avg_score))

        must_human = (
            risk_assessment.must_human_review
            or risk_assessment.severity.value == "high"
        )

        return DraftReply(
            ticket_id="",
            draft_text=draft_text,
            citations=citations,
            evidence_used=citations,
            unsupported_claims=[],
            missing_information=[],
            confidence=confidence,
            must_human_review=must_human,
        )
