"""Agentic draft generation with tool use and multi-step reasoning.

DraftAgent replaces the direct single-shot LLM call with an agentic loop:
  1. Retrieve — call ``search_knowledge`` to get evidence
  2. Evaluate — assess evidence quality and coverage
  3. Decide  — reformulate query if evidence is insufficient
  4. Generate — produce reply grounded in evidence
  5. Verify  — self-check for hallucination and unsupported claims

Uses DeepSeek (or any OpenAI-compatible endpoint) as the agent brain.
Tools are prompt-based (structured JSON output), not function-calling API.

Architecture
------------
Logic is split across five sibling modules — ``llm_utils``, ``knowledge_tools``,
``search_refiner``, ``generation``, and ``reflection`` — that this class
orchestrates.
"""

from __future__ import annotations

import contextlib
import logging
import os
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from ticketpilot.drafting.generation import (
    build_fallback,
    generate_reply,
    verify_reply,
)
from ticketpilot.drafting.knowledge_tools import search_knowledge
from ticketpilot.drafting.llm_utils import LlmConfig
from ticketpilot.drafting.reflection import reflect_and_revise, skill_reflect
from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.drafting.search_refiner import llm_guided_search, reformulate_search
from ticketpilot.guardrails import run_guardrails
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import Ticket
from ticketpilot.tracing import AgentTrace, create_trace

logger = logging.getLogger(__name__)

# Minimum RRF score threshold for evidence to be considered "good"
_EVIDENCE_SCORE_THRESHOLD = 0.01
# Maximum evidence items to keep (prevents unbounded context growth)
_MAX_EVIDENCE = 15


# ---------------------------------------------------------------------------
# Mutable state tracked across agent loop iterations
# ---------------------------------------------------------------------------


@dataclass
class _AgentState:
    """Mutable state tracked across agent loop iterations."""

    evidence: list[EvidenceCandidate] = field(default_factory=list)
    search_queries_used: list[str] = field(default_factory=list)
    iterations: int = 0


# ---------------------------------------------------------------------------
# DraftAgent
# ---------------------------------------------------------------------------


class DraftAgent:
    """Agentic draft generator with tool use and multi-step reasoning.

    Uses an LLM (DeepSeek by default) to iteratively:
    1. Search knowledge base for evidence
    2. Evaluate evidence quality
    3. Reformulate queries if needed
    4. Generate evidence-grounded reply
    5. Self-verify against hallucination

    Configuration is read from environment variables:

    * ``TICKETPILOT_LLM_BASE_URL``
    * ``TICKETPILOT_LLM_API_KEY``
    * ``TICKETPILOT_LLM_MODEL``
    * ``TICKETPILOT_LLM_TIMEOUT_SECONDS``
    * ``TICKETPILOT_LLM_MAX_TOKENS``
    * ``TICKETPILOT_LLM_TEMPERATURE``
    """

    def __init__(self, template_id: str = "default") -> None:
        self._base_url = os.environ.get(
            "TICKETPILOT_LLM_BASE_URL", "https://api.deepseek.com"
        ).rstrip("/")
        self._api_key = os.environ.get("TICKETPILOT_LLM_API_KEY", "")
        self._model = os.environ.get(
            "TICKETPILOT_LLM_MODEL", "deepseek-chat"
        )
        self._timeout = int(
            os.environ.get("TICKETPILOT_LLM_TIMEOUT_SECONDS", "60")
        )
        self._max_tokens = int(
            os.environ.get("TICKETPILOT_LLM_MAX_TOKENS", "1024")
        )
        self._temperature = float(
            os.environ.get("TICKETPILOT_LLM_TEMPERATURE", "0.3")
        )
        self._template_id = template_id

    @property
    def _llm_config(self) -> LlmConfig:
        """Build an :class:`LlmConfig` from the current instance attributes."""
        return LlmConfig(
            base_url=self._base_url,
            api_key=self._api_key,
            model=self._model,
            timeout=self._timeout,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
        )

    def __repr__(self) -> str:
        return (
            f"DraftAgent(base_url={self._base_url!r}, "
            f"model={self._model!r}, template_id={self._template_id!r})"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_draft(
        self,
        normalized_text: str | Ticket,
        issue_type: str = "",
        risk_flags: list[str] | None = None,
        severity: str = "low",
        must_human_review: bool = False,
        evidence_candidates: list[EvidenceCandidate] | None = None,
    ) -> DraftReply:
        """Run the agentic loop to produce a ``DraftReply``.

        Args:
            normalized_text: Customer's normalized message text, or a
                ``Ticket`` object.
            issue_type: Classified intent / issue type.
            risk_flags: Detected risk flags.
            severity: Risk severity level.
            must_human_review: Whether risk assessment requires human review.
            evidence_candidates: Pre-retrieved evidence (used as initial
                context).

        Returns:
            ``DraftReply`` with citations, confidence, and guard flags.
        """
        # Accept a Ticket object for convenience
        if isinstance(normalized_text, Ticket):
            ticket = normalized_text
            normalized_text = ticket.text
            issue_type = ticket.intent.value
            risk_flags = [f.value for f in ticket.risk_flags]
        flags = risk_flags or []
        state = _AgentState()

        # Create trace
        trace = create_trace(
            agent_name="DraftAgent",
            input_data={
                "normalized_text": normalized_text,
                "issue_type": issue_type,
                "risk_flags": flags,
                "severity": severity,
                "must_human_review": must_human_review,
                "evidence_count": len(evidence_candidates)
                if evidence_candidates
                else 0,
            },
        )

        # Seed state with any pre-retrieved evidence (capped)
        if evidence_candidates:
            sorted_candidates = sorted(
                evidence_candidates, key=lambda e: e.score, reverse=True
            )
            state.evidence = sorted_candidates[:_MAX_EVIDENCE]

        try:
            result = self._run_agent_loop(
                normalized_text=normalized_text,
                issue_type=issue_type,
                flags=flags,
                severity=severity,
                must_human_review=must_human_review,
                state=state,
                trace=trace,
            )

            # Skill-based self-reflection (optional, graceful fallback)
            with (
                trace.step("skill_reflect")
                if trace
                else contextlib.nullcontext() as step
            ):
                result = skill_reflect(
                    result=result,
                    issue_type=issue_type,
                    flags=flags,
                )
                if step:
                    step.finish({"applied": True})

            # Run guardrails
            with (
                trace.step("guardrails")
                if trace
                else contextlib.nullcontext() as step
            ):
                guardrail_results = run_guardrails(
                    input_text=normalized_text,
                    output_text=result.draft_text,
                    confidence=result.confidence,
                )

                # Check if any guardrail failed
                failed_guardrails = [
                    g
                    for g in guardrail_results
                    if not g.passed and g.severity == "error"
                ]
                if failed_guardrails:
                    logger.warning(
                        "DraftAgent: guardrails failed: %s",
                        [g.check_name for g in failed_guardrails],
                    )
                    result.must_human_review = True
                    result.safety_notes.extend(
                        [g.message for g in failed_guardrails]
                    )

                if step:
                    step.finish(
                        {
                            "passed": len(
                                [g for g in guardrail_results if g.passed]
                            ),
                            "failed": len(
                                [
                                    g
                                    for g in guardrail_results
                                    if not g.passed
                                ]
                            ),
                            "checks": [
                                g.check_name for g in guardrail_results
                            ],
                        }
                    )

            # Finish trace
            trace.finish(
                output_data={
                    "draft_text": result.draft_text[:200],
                    "confidence": result.confidence,
                    "must_human_review": result.must_human_review,
                    "citations_count": len(result.citations),
                }
            )

            # Save trace
            from ticketpilot.tracing import get_trace_collector

            get_trace_collector().save_trace(trace)

            return result
        except Exception as e:
            logger.error("DraftAgent failed: %s", e, exc_info=True)

            # Finish trace with error
            trace.finish(error=str(e))
            from ticketpilot.tracing import get_trace_collector

            get_trace_collector().save_trace(trace)

            return build_fallback(
                reason="agent_error",
                flags=flags,
                must_human_review=must_human_review,
                error_msg=str(e),
            )

    # ------------------------------------------------------------------
    # Agent loop internals
    # ------------------------------------------------------------------

    def _run_agent_loop(
        self,
        normalized_text: str,
        issue_type: str,
        flags: list[str],
        severity: str,
        must_human_review: bool,
        state: _AgentState,
        trace: AgentTrace | None = None,
    ) -> DraftReply:
        """Core agent loop: retrieve → evaluate → decide → generate → verify."""

        # Step 1: Initial retrieval if no evidence pre-seeded
        if not state.evidence:
            with (
                trace.step(
                    "retrieve",
                    {"query": f"{normalized_text} {issue_type}"},
                )
                if trace
                else contextlib.nullcontext() as step
            ):
                initial_query = f"{normalized_text} {issue_type}"
                state.search_queries_used.append(initial_query)
                raw_results = search_knowledge(initial_query)
                state.evidence = self._raw_results_to_candidates(raw_results)
                if step:
                    step.finish({"evidence_count": len(state.evidence)})
                logger.info(
                    "DraftAgent: initial search returned %d results",
                    len(state.evidence),
                )

        # Step 2-3: Evaluate evidence and optionally reformulate
        if state.evidence:
            avg_score = (
                sum(e.score for e in state.evidence) / len(state.evidence)
            )
            if (
                avg_score < _EVIDENCE_SCORE_THRESHOLD
                or len(state.evidence) < 2
            ):
                with (
                    trace.step(
                        "reformulate",
                        {
                            "avg_score": avg_score,
                            "evidence_count": len(state.evidence),
                        },
                    )
                    if trace
                    else contextlib.nullcontext() as step
                ):
                    logger.info(
                        "DraftAgent: evidence quality low (avg=%.4f, n=%d), "
                        "reformulating",
                        avg_score,
                        len(state.evidence),
                    )
                    reformulate_search(
                        normalized_text=normalized_text,
                        issue_type=issue_type,
                        evidence=state.evidence,
                        search_queries_used=state.search_queries_used,
                        search_knowledge_fn=search_knowledge,
                        raw_results_to_candidates_fn=self._raw_results_to_candidates,
                        max_evidence=_MAX_EVIDENCE,
                    )
                    if step:
                        step.finish(
                            {"new_evidence_count": len(state.evidence)}
                        )

        # If still no evidence, use LLM to try one more search
        if not state.evidence:
            with (
                trace.step("llm_guided_search")
                if trace
                else contextlib.nullcontext() as step
            ):
                logger.info(
                    "DraftAgent: no evidence found, asking LLM for search query"
                )
                llm_guided_search(
                    normalized_text=normalized_text,
                    issue_type=issue_type,
                    evidence=state.evidence,
                    search_queries_used=state.search_queries_used,
                    search_knowledge_fn=search_knowledge,
                    raw_results_to_candidates_fn=self._raw_results_to_candidates,
                    llm_config=self._llm_config,
                    max_evidence=_MAX_EVIDENCE,
                )
                if step:
                    step.finish({"evidence_count": len(state.evidence)})

        # Step 4: Generate reply
        if state.evidence:
            with (
                trace.step(
                    "generate", {"evidence_count": len(state.evidence)}
                )
                if trace
                else contextlib.nullcontext() as step
            ):
                draft_result = generate_reply(
                    normalized_text=normalized_text,
                    issue_type=issue_type,
                    flags=flags,
                    severity=severity,
                    must_human_review=must_human_review,
                    evidence=state.evidence,
                    llm_config=self._llm_config,
                    template_id=self._template_id,
                )
                if step:
                    step.finish({"has_draft": draft_result is not None})
        else:
            logger.info(
                "DraftAgent: no evidence after all attempts, using fallback"
            )
            draft_result = None

        # Step 5: Self-reflection and revision
        if draft_result is not None:
            with (
                trace.step("reflect_and_revise")
                if trace
                else contextlib.nullcontext() as step
            ):
                draft_result = reflect_and_revise(
                    draft_result=draft_result,
                    normalized_text=normalized_text,
                    issue_type=issue_type,
                    evidence=state.evidence,
                    flags=flags,
                    must_human_review=must_human_review,
                    llm_config=self._llm_config,
                )
                if step:
                    step.finish(
                        {"confidence": draft_result.get("confidence", 0)}
                    )

            # Step 6: Final verification
            with (
                trace.step("verify")
                if trace
                else contextlib.nullcontext() as step
            ):
                verified = verify_reply(
                    draft_result=draft_result,
                    evidence=state.evidence,
                    flags=flags,
                    must_human_review=must_human_review,
                    build_fallback_fn=build_fallback,
                    search_queries=state.search_queries_used,
                )
                if step:
                    step.finish(
                        {
                            "confidence": verified.confidence,
                            "must_human_review": verified.must_human_review,
                            "citations_count": len(verified.citations),
                        }
                    )
                return verified

        return build_fallback(
            reason="insufficient_evidence",
            flags=flags,
            must_human_review=True,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _raw_results_to_candidates(
        raw_results: list[dict[str, Any]],
    ) -> list[EvidenceCandidate]:
        """Convert raw search result dicts to ``EvidenceCandidate`` objects."""
        candidates: list[EvidenceCandidate] = []
        for i, r in enumerate(raw_results):
            try:
                candidates.append(
                    EvidenceCandidate(
                        chunk_id=UUID(r["chunk_id"]),
                        doc_id=UUID(r["doc_id"]),
                        doc_type=DocType(r["doc_type"]),
                        source_id=UUID(
                            r.get("source_id", r["doc_id"])
                        ),
                        source_table=r.get("source_table", ""),
                        content=r.get("content", ""),
                        score=r.get("score", 0.0),
                        rank=r.get("rank", i + 1),
                        title=r.get("title"),
                    )
                )
            except (KeyError, ValueError) as e:
                logger.warning(
                    "DraftAgent: skipping malformed result: %s", e
                )
        return candidates
