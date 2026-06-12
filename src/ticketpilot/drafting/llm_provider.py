"""LLM provider interface and deterministic FakeLLMProvider."""

from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

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

        # Build guard-aware structured prompt
        system_prompt = (
            "你是一名客服工单处理助手。请根据用户消息和检索到的证据，生成一个专业的回复草稿。"
            "回复必须基于提供的证据内容来组织回答，不要编造证据中没有的信息。"
            "即使证据相关度评分较低，只要内容与用户问题相关，就应当基于这些证据给出回复。"
            "只有当完全没有可用证据时，才建议转人工。"
            "回复用中文。"
        )

        # Guard-aware safety rules
        # Build a mapping: chunk_id -> [N] for numbered citations
        sorted_evidence_for_prompt = sorted(evidence, key=lambda e: e.rank)[:5]
        id_to_num: dict[str, int] = {}
        for idx, ev in enumerate(sorted_evidence_for_prompt, start=1):
            id_to_num[str(ev.chunk_id)] = idx

        safety_rules = [
            "## 安全与约束规则",
            "1. 引用格式：在回复中引用证据时，使用数字编号 [1]、[2]、[3] 格式，对应下方证据列表的编号。",
            "   示例：根据退货政策 [1]，商品需在7天内保持原包装。",
            "2. 只有当提供的证据列表为空（没有任何证据条目）时，才说明无法确认并建议转人工。",
            "3. 禁止承诺退款金额（如：退款100元）、赔偿金额、法律行动、账号变更。",
            "4. 禁止承诺解决时间线（如：3天内解决）或保证特定结果。",
            "5. 禁止承认法律责任或做出超出证据范围的保证。",
            "6. 严格保持证据原文的主语和措辞。不要替换主语，不要夸大程度，不要添加原文没有的时间承诺。",
            "7. 独立信息必须用分号或换行分隔，绝对不能合并成一句。",
            "8. 回复结构：第一步共情（用一句话理解用户感受），第二步方案（具体可执行的步骤），第三步时间（如有明确时间才写）。",
            "9. 只回应用户的核心问题。不要添加与当前问题无直接关系的承诺。回复聚焦在解决用户当前的具体诉求上。",
            "10. 不要在回复中提及「草稿」「审核」「人工复核」等内部流程词。回复语气应专业、自然，像正式客服回复。",
        ]
        if severity in ("high", "critical"):
            safety_rules.append(
                f"7. 注意：本工单严重程度为「{severity}」，必须建议客户转人工处理。"
            )
        if flags:
            safety_rules.append(
                f"8. 本工单包含风险标记：{', '.join(flags)}，回复中必须说明已升级至人工审核。"
            )

        # Format evidence with numbered labels instead of raw chunk_ids
        evidence_lines: list[str] = []
        for idx, ev in enumerate(sorted_evidence_for_prompt, start=1):
            doc_type = ev.doc_type.value if hasattr(ev.doc_type, 'value') else str(ev.doc_type)
            evidence_lines.append(
                f"[{idx}] ({doc_type}) {ev.content[:200]}"
            )
        numbered_evidence = "\n".join(evidence_lines)

        user_prompt = (
            f"用户消息：{normalized_text}\n"
            f"问题类型：{issue_type}\n"
            f"风险标记：{flags}\n"
            f"严重度：{severity}\n\n"
            f"## 可用证据\n{numbered_evidence}\n\n"
            + "\n".join(safety_rules)
            + "\n\n请生成回复（引用证据时使用 [1]、[2] 等编号格式）："
        )

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

        except Exception as exc:  # noqa: BLE001
            logger.error("LLM provider failed: %s", exc, exc_info=True)
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
