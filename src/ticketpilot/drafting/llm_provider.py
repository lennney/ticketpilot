"""LLM provider interface and deterministic FakeLLMProvider."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

import urllib.request
import urllib.error

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
        """Model identifier used by this provider (e.g. 'fake', 'gpt-4o-mini')."""
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

        # Build deterministic draft text using [chunk_id] markers for claim guard
        cited_ids = [str(ev.chunk_id) for ev in top_n]
        lines: list[str] = [
            f"您好，关于您反馈的{issue_type}问题，",
        ]
        for ev in top_n:
            title = getattr(ev, "title", None)
            label = f"（{title}）" if title else ""
            lines.append(
                f"根据相关资料{label}[{ev.chunk_id}]，{ev.content[:100]}。"
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


class OpenAICompatibleProvider(LLMProvider):
    """OpenAI-compatible LLM provider for real draft generation.

    Calls OpenAI-compatible API endpoint with chat completions format.
    Safe fallback on errors. Never logs API key.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str = "gpt-4o-mini",
        timeout_seconds: int = 30,
        max_tokens: int = 512,
        temperature: float = 0.3,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._max_tokens = max_tokens
        self._temperature = temperature

    @property
    def provider_name(self) -> str:
        return "openai_compatible"

    @property
    def model_name(self) -> str:
        return self._model

    def __repr__(self) -> str:
        """Safe repr that does not expose API key."""
        return (
            f"OpenAICompatibleProvider(base_url={self._base_url!r}, "
            f"model={self._model!r})"
        )

    def generate_draft(
        self,
        normalized_text: str,
        issue_type: str,
        risk_flags: list[str] | None = None,
        severity: str = "low",
        must_human_review: bool = False,
        evidence_candidates: list[EvidenceCandidate] | None = None,
    ) -> DraftReply:
        """Generate draft via OpenAI-compatible API.

        On error, returns safe fallback DraftReply with must_human_review=True.
        """
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

        # Build prompt from evidence
        system_prompt = (
            "你是一个客服工单处理助手。根据用户消息和检索到的证据，生成一个专业的回复草稿。"
            "回复必须基于提供的证据，不要编造信息。如果无法找到相关证据，说明无法确认并建议转人工。"
            "回复用中文。"
        )

        evidence_text = ""
        for i, ev in enumerate(evidence[:5], start=1):
            title = getattr(ev, "title", "")
            evidence_text += f"\n[{i}] {title}: {ev.content[:200]}"

        user_prompt = f"用户消息：{normalized_text}\n问题类型：{issue_type}\n风险标记：{flags}\n严重度：{severity}\n检索到的证据：{evidence_text}\n\n请生成回复草稿："

        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
        }

        try:
            req = urllib.request.Request(
                f"{self._base_url}/chat/completions",
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                result = json.loads(resp.read().decode("utf-8"))

            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Build citations
            from ticketpilot.drafting.schemas import Citation as CitationModel

            sorted_evidence = sorted(evidence, key=lambda e: e.rank)
            top_n = sorted_evidence[:3]
            citations: list[CitationModel] = []
            cited_ids: list[str] = []
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
                cited_ids.append(str(ev.chunk_id))

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
                draft_text=content,
                citations=citations,
                evidence_used=citations,
                unsupported_claims=[],
                missing_information=[],
                confidence=0.7,
                must_human_review=needs_review,
                provider_id=self.provider_name,
                escalation_reason=escalation_reason,
                safety_notes=safety_notes,
                cited_evidence_ids=cited_ids,
            )

        except Exception:  # noqa: BLE001
            # Safe fallback on any error
            return DraftReply(
                ticket_id="",
                draft_text=SAFE_FALLBACK_TEXT,
                citations=[],
                evidence_used=[],
                unsupported_claims=["API调用失败，无法生成草稿"],
                missing_information=["API调用失败"],
                confidence=0.0,
                must_human_review=True,
                fallback_reason="api_error",
                provider_id=self.provider_name,
                escalation_reason="api_call_failed",
                safety_notes=["LLM API调用失败，返回安全回退草稿"],
                cited_evidence_ids=[],
            )
