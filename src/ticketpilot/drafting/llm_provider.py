"""LLM provider interface and deterministic FakeLLMProvider."""

from __future__ import annotations

from abc import ABC, abstractmethod

from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.schema.evidence import EvidenceCandidate

SAFE_FALLBACK_TEXT = "根据现有信息，无法确认具体政策条款，建议转人工处理。"


class LLMProvider(ABC):
    """Abstract interface for LLM draft generation providers.

    Subclasses must implement provider_name, model_name, and generate_draft.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable provider identifier (e.g. 'fake', 'openai_compatible')."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier used by this provider (e.g. 'fake', 'gpt-4')."""
        ...

    @abstractmethod
    def generate_draft(
        self,
        normalized_text: str,
        issue_type: str,
        risk_flags: list[str] | None = None,
        severity: str = "low",
        must_human_review: bool = False,
        evidence_candidates: list[EvidenceCandidate] | None = None,
    ) -> DraftReply:
        """Generate a draft reply from ticket context and evidence.

        Args:
            normalized_text: The customer's normalized message text.
            issue_type: Classified issue type / intent.
            risk_flags: Risk flags detected for this ticket.
            severity: Risk severity level.
            must_human_review: Whether risk assessment already requires human review.
            evidence_candidates: Retrieved evidence candidates from the knowledge base.

        Returns:
            DraftReply with citations and guard flags.
        """
        ...


class FakeLLMProvider(LLMProvider):
    """Deterministic fake LLM provider for development and testing.

    Produces stable template-based output from evidence candidates.
    Never calls network, never requires API keys.
    """

    @property
    def provider_name(self) -> str:
        return "fake"

    @property
    def model_name(self) -> str:
        return "fake"

    def generate_draft(
        self,
        normalized_text: str,
        issue_type: str,
        risk_flags: list[str] | None = None,
        severity: str = "low",
        must_human_review: bool = False,
        evidence_candidates: list[EvidenceCandidate] | None = None,
    ) -> DraftReply:
        flags = risk_flags or []
        evidence = evidence_candidates or []

        # No-evidence fallback
        if not evidence:
            return DraftReply(
                ticket_id="",
                draft_text=SAFE_FALLBACK_TEXT,
                citations=[],
                evidence_used=[],
                unsupported_claims=[],
                missing_information=["未找到相关证据"],
                confidence=0.0,
                must_human_review=True,
                fallback_reason="no_evidence",
                provider_id=self.provider_name,
                escalation_reason="insufficient_evidence",
                safety_notes=["未检索到相关证据，无法生成有依据的回复"],
                cited_evidence_ids=[],
            )

        # Sort by rank ascending, take top 3
        sorted_evidence = sorted(evidence, key=lambda e: e.rank)
        top_n = sorted_evidence[:3]

        # Build citations
        from ticketpilot.drafting.schemas import Citation as CitationModel

        citations: list[CitationModel] = []
        for ev in top_n:
            citations.append(
                CitationModel(
                    chunk_id=ev.chunk_id,
                    doc_id=ev.doc_id,
                    doc_type=ev.doc_type,
                    source_table=getattr(ev, "source_table", ""),
                    source_id=getattr(ev, "source_id", ev.doc_id),
                    evidence_excerpt=ev.content[:200],
                    claim_supported=True,
                )
            )

        # Build deterministic draft text
        cited_ids = [str(ev.chunk_id) for ev in top_n]
        lines: list[str] = [
            f"您好，关于您反馈的{issue_type}问题，",
        ]
        for i, ev in enumerate(top_n, start=1):
            title = getattr(ev, "title", None)
            label = f"（{title}）" if title else ""
            lines.append(
                f"根据相关资料{label}[{i}]，{ev.content[:100]}。"
            )
        lines.append("")
        lines.append("希望以上信息对您有帮助。如有其他问题，请随时联系我们。")

        draft_text = "\n".join(lines)

        # Confidence from average evidence score
        avg_score = sum(e.score for e in top_n) / len(top_n)
        confidence = max(0.0, min(1.0, avg_score))

        # Human review if risk flags exist or already required
        needs_review = must_human_review or bool(flags)

        safety_notes: list[str] = []
        if flags:
            safety_notes.append(f"工单含风险标记：{', '.join(flags)}，需人工审核")

        escalation_reason: str | None = None
        if needs_review:
            if flags:
                escalation_reason = f"risk_flags: {', '.join(flags)}"
            elif must_human_review:
                escalation_reason = "risk_assessment_requires_review"

        return DraftReply(
            ticket_id="",
            draft_text=draft_text,
            citations=citations,
            evidence_used=citations,
            unsupported_claims=[],
            missing_information=[],
            confidence=confidence,
            must_human_review=needs_review,
            provider_id=self.provider_name,
            escalation_reason=escalation_reason,
            safety_notes=safety_notes,
            cited_evidence_ids=cited_ids,
        )
