"""Agentic draft generation with tool use and multi-step reasoning.

DraftAgent replaces the direct single-shot LLM call with an agentic loop:
  1. Retrieve — call search_knowledge to get evidence
  2. Evaluate — assess evidence quality and coverage
  3. Decide  — reformulate query if evidence is insufficient
  4. Generate — produce reply grounded in evidence
  5. Verify  — self-check for hallucination and unsupported claims

Uses DeepSeek (or any OpenAI-compatible endpoint) as the agent brain.
Tools are prompt-based (structured JSON output), not function-calling API.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from ticketpilot.drafting.schemas import Citation, DraftReply
from ticketpilot.retrieval.evidence_mapper import map_fused_to_evidence
from ticketpilot.retrieval.pipeline import hybrid_retrieval
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.schema.evidence import EvidenceCandidate
from ticketpilot.schema.ticket import Ticket
from ticketpilot.tracing import create_trace, AgentTrace
from ticketpilot.guardrails import run_guardrails, GuardrailResult
from ticketpilot.skills.loader import load_skill_library, select_relevant_skills
from ticketpilot.skills.reflector import reflect_on_draft

logger = logging.getLogger(__name__)

# Minimum RRF score threshold for evidence to be considered "good"
_EVIDENCE_SCORE_THRESHOLD = 0.01
# Maximum agent loop iterations (safety bound)
_MAX_ITERATIONS = 5
# Safe fallback when agent cannot produce a grounded reply
SAFE_FALLBACK_TEXT = "根据现有信息，无法确认具体政策条款，建议转人工处理。"

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
你是一名客服工单处理智能助手（DraftAgent）。
你的任务是根据客户消息，使用提供的工具检索知识库，然后生成基于证据的专业回复。

## 可用工具

### 1. search_knowledge
用途：在知识库中搜索与客户问题相关的证据（FAQ、政策、案例）。
输入格式：
```json
{"tool": "search_knowledge", "query": "搜索关键词"}
```

### 2. get_policy_by_code
用途：根据政策编号查找具体政策内容。
输入格式：
```json
{"tool": "get_policy_by_code", "code": "1.2.3"}
```

## 工作流程

1. 首先使用 search_knowledge 检索证据
2. 评估检索到的证据质量（相关性评分、内容覆盖度）
3. 如果证据不足，尝试用不同的关键词重新搜索
4. 基于证据生成回复草稿
5. 自我检查回复是否基于证据，有无编造内容

## 安全规则

- 回复必须基于检索到的证据，禁止编造信息
- 禁止承诺退款金额、赔偿金额、法律行动、账号变更
- 禁止承诺解决时间线或保证特定结果
- 禁止承认法律责任或做出超出证据范围的保证
- 如果证据不足以回答客户问题，必须建议转人工处理
- 引用证据时使用 [证据ID] 格式

## 输出格式

当需要调用工具时，输出：
```json
{"tool": "工具名", "参数名": "参数值"}
```

当准备好生成最终回复时，输出：
```json
{
  "step": "reply",
  "draft_text": "回复内容",
  "cited_evidence_ids": ["证据ID1", "证据ID2"],
  "confidence": 0.8,
  "unsupported_claims": ["无法支持的内容（如有）"],
  "missing_information": ["缺失信息（如有）"],
  "safety_notes": ["安全说明（如有）"]
}
```
"""

_EVALUATE_PROMPT = """\
你刚刚检索到了以下证据：

{evidence_summary}

客户问题：{normalized_text}
问题类型：{issue_type}

请评估这些证据：
1. 证据是否足以回答客户问题？（是/否）
2. 最相关的证据是哪些？（列出证据ID）
3. 是否需要补充搜索？如果需要，建议搜索什么关键词？

直接给出评估结论，不需要调用工具。"""


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class _AgentState:
    """Mutable state tracked across agent loop iterations."""

    evidence: list[EvidenceCandidate] = field(default_factory=list)
    search_queries_used: list[str] = field(default_factory=list)
    iterations: int = 0
    evaluation_notes: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _search_knowledge(query: str, top_k: int = 10) -> list[dict[str, Any]]:
    """Search the knowledge base using hybrid retrieval.

    Returns a list of dicts with chunk_id, doc_type, content, score, rank.
    """
    try:
        trace = hybrid_retrieval(query=query, top_k=top_k)
        candidates = map_fused_to_evidence(trace.fused_results)
        results = []
        for c in candidates:
            results.append({
                "chunk_id": str(c.chunk_id),
                "doc_id": str(c.doc_id),
                "doc_type": c.doc_type.value,
                "content": c.content[:300],
                "score": round(c.score, 4),
                "rank": c.rank,
                "title": c.title,
                "source_table": c.source_table,
                "source_id": str(c.source_id),
            })
        return results
    except Exception as e:
        logger.error("search_knowledge failed: %s", e)
        return []


def _get_policy_by_code(code: str) -> str:
    """Look up a specific policy document by its policy code (e.g. '1.2.3').

    Returns the policy content as a string, or an error message.
    """
    # Validate format
    parts = code.split(".")
    if len(parts) != 3 or not all(p.isdigit() for p in parts):
        return f"无效的政策编号格式: {code}，正确格式为 X.Y.Z"

    try:
        from ticketpilot.retrieval.db.connection import get_db_connection

        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT title, content, effective_date FROM knowledge_policy "
                    "WHERE policy_code = %s LIMIT 1",
                    (code,),
                )
                row = cur.fetchone()
                if row:
                    title, content, effective_date = row
                    return (
                        f"政策编号: {code}\n"
                        f"标题: {title}\n"
                        f"生效日期: {effective_date}\n"
                        f"内容: {content}"
                    )
                return f"未找到编号为 {code} 的政策"
    except Exception as e:
        logger.error("get_policy_by_code failed: %s", e)
        return f"查询政策时出错: {e}"


# ---------------------------------------------------------------------------
# LLM call helper
# ---------------------------------------------------------------------------


def _call_llm(
    messages: list[dict[str, str]],
    base_url: str,
    api_key: str,
    model: str,
    timeout: int,
    max_tokens: int,
    temperature: float,
) -> str:
    """Make a single chat completion call to the LLM endpoint."""
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result.get("choices", [{}])[0].get("message", {}).get("content", "")


def _extract_json(text: str) -> dict[str, Any] | None:
    """Extract a JSON object from LLM output (handles markdown fences)."""
    # Try to find JSON block in markdown code fence
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Try parsing the entire text as JSON
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Try to find first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


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
        TICKETPILOT_LLM_BASE_URL, TICKETPILOT_LLM_API_KEY,
        TICKETPILOT_LLM_MODEL, TICKETPILOT_LLM_TIMEOUT_SECONDS,
        TICKETPILOT_LLM_MAX_TOKENS, TICKETPILOT_LLM_TEMPERATURE
    """

    def __init__(self, template_id: str = "default") -> None:
        self._base_url = os.environ.get(
            "TICKETPILOT_LLM_BASE_URL", "https://api.deepseek.com"
        ).rstrip("/")
        self._api_key = os.environ.get("TICKETPILOT_LLM_API_KEY", "")
        self._model = os.environ.get("TICKETPILOT_LLM_MODEL", "deepseek-chat")
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
        """Run the agentic loop to produce a DraftReply.

        Args:
            normalized_text: Customer's normalized message text, or a Ticket object.
            issue_type: Classified intent / issue type.
            risk_flags: Detected risk flags.
            severity: Risk severity level.
            must_human_review: Whether risk assessment requires human review.
            evidence_candidates: Pre-retrieved evidence (used as initial context).

        Returns:
            DraftReply with citations, confidence, and guard flags.
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
                "evidence_count": len(evidence_candidates) if evidence_candidates else 0,
            }
        )

        # Seed state with any pre-retrieved evidence
        if evidence_candidates:
            state.evidence = list(evidence_candidates)

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
            with trace.step("skill_reflect") if trace else contextlib.nullcontext() as step:
                result = self._skill_reflect(
                    result=result,
                    issue_type=issue_type,
                    flags=flags,
                )
                if step:
                    step.finish({"applied": True})

            # Run guardrails
            with trace.step("guardrails") if trace else contextlib.nullcontext() as step:
                guardrail_results = run_guardrails(
                    input_text=normalized_text,
                    output_text=result.draft_text,
                    confidence=result.confidence,
                )
                
                # Check if any guardrail failed
                failed_guardrails = [g for g in guardrail_results if not g.passed and g.severity == "error"]
                if failed_guardrails:
                    logger.warning("DraftAgent: guardrails failed: %s", [g.check_name for g in failed_guardrails])
                    # Mark for human review
                    result.must_human_review = True
                    result.safety_notes.extend([g.message for g in failed_guardrails])
                
                if step:
                    step.finish({
                        "passed": len([g for g in guardrail_results if g.passed]),
                        "failed": len([g for g in guardrail_results if not g.passed]),
                        "checks": [g.check_name for g in guardrail_results],
                    })
            
            # Finish trace
            trace.finish(output_data={
                "draft_text": result.draft_text[:200],
                "confidence": result.confidence,
                "must_human_review": result.must_human_review,
                "citations_count": len(result.citations),
            })
            
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
            
            return self._build_fallback(
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
            with trace.step("retrieve", {"query": f"{normalized_text} {issue_type}"}) if trace else contextlib.nullcontext() as step:
                initial_query = f"{normalized_text} {issue_type}"
                state.search_queries_used.append(initial_query)
                raw_results = _search_knowledge(initial_query)
                state.evidence = self._raw_results_to_candidates(raw_results)
                if step:
                    step.finish({"evidence_count": len(state.evidence)})
                logger.info(
                    "DraftAgent: initial search returned %d results", len(state.evidence)
                )

        # Step 2-3: Evaluate evidence and optionally reformulate
        if state.evidence:
            avg_score = sum(e.score for e in state.evidence) / len(state.evidence)
            if avg_score < _EVIDENCE_SCORE_THRESHOLD or len(state.evidence) < 2:
                with trace.step("reformulate", {"avg_score": avg_score, "evidence_count": len(state.evidence)}) if trace else contextlib.nullcontext() as step:
                    logger.info(
                        "DraftAgent: evidence quality low (avg=%.4f, n=%d), reformulating",
                        avg_score,
                        len(state.evidence),
                    )
                    self._reformulate_search(normalized_text, issue_type, state)
                    if step:
                        step.finish({"new_evidence_count": len(state.evidence)})

        # If still no evidence, use LLM to try one more search
        if not state.evidence:
            with trace.step("llm_guided_search") if trace else contextlib.nullcontext() as step:
                logger.info("DraftAgent: no evidence found, asking LLM for search query")
                self._llm_guided_search(normalized_text, issue_type, state)
                if step:
                    step.finish({"evidence_count": len(state.evidence)})

        # Step 4: Generate reply
        # If we have evidence, use LLM to generate; otherwise use fallback
        if state.evidence:
            with trace.step("generate", {"evidence_count": len(state.evidence)}) if trace else contextlib.nullcontext() as step:
                draft_result = self._generate_reply(
                    normalized_text=normalized_text,
                    issue_type=issue_type,
                    flags=flags,
                    severity=severity,
                    must_human_review=must_human_review,
                    evidence=state.evidence,
                )
                if step:
                    step.finish({"has_draft": draft_result is not None})
        else:
            logger.info("DraftAgent: no evidence after all attempts, using fallback")
            draft_result = None

        # Step 5: Self-reflection and revision
        if draft_result is not None:
            with trace.step("reflect_and_revise") if trace else contextlib.nullcontext() as step:
                # Reflect on the draft quality
                draft_result = self._reflect_and_revise(
                    draft_result=draft_result,
                    normalized_text=normalized_text,
                    issue_type=issue_type,
                    evidence=state.evidence,
                    flags=flags,
                    must_human_review=must_human_review,
                )
                if step:
                    step.finish({"confidence": draft_result.get("confidence", 0)})

            # Step 6: Final verification
            with trace.step("verify") if trace else contextlib.nullcontext() as step:
                verified = self._verify_reply(
                    draft_result=draft_result,
                    evidence=state.evidence,
                    flags=flags,
                    must_human_review=must_human_review,
                )
                if step:
                    step.finish({
                        "confidence": verified.confidence,
                        "must_human_review": verified.must_human_review,
                        "citations_count": len(verified.citations),
                    })
                return verified

        return self._build_fallback(
            reason="insufficient_evidence",
            flags=flags,
            must_human_review=True,
        )

    def _reflect_and_revise(
        self,
        draft_result: dict[str, Any],
        normalized_text: str,
        issue_type: str,
        evidence: list[EvidenceCandidate],
        flags: list[str],
        must_human_review: bool,
        max_revisions: int = 1,
    ) -> dict[str, Any]:
        """
        Self-reflection loop: critique the draft and revise if needed.
        
        Implements the Critique → Revise pattern from industry best practices.
        Reduces hallucination by checking if the draft is grounded in evidence.
        
        Args:
            draft_result: Initial draft from LLM
            normalized_text: Customer's normalized message
            issue_type: Classified intent
            evidence: Retrieved evidence
            flags: Risk flags
            must_human_review: Whether human review is required
            max_revisions: Maximum number of revision attempts
        
        Returns:
            Revised draft_result (or original if critique passes)
        """
        draft_text = draft_result.get("draft_text", "")
        
        if not draft_text or not evidence:
            return draft_result
        
        # Build evidence summary for critique
        evidence_summary = "\n".join(
            f"[{i+1}] {e.content[:200]}"
            for i, e in enumerate(evidence[:5])
        )
        
        for revision in range(max_revisions):
            # Ask LLM to critique the draft
            critique_prompt = f"""你是一名质量审核专家。请审核以下客服回复草稿。

客户问题：{normalized_text}
问题类型：{issue_type}

检索到的证据：
{evidence_summary}

回复草稿：
{draft_text}

请从以下维度审核：
1. 回复是否基于证据？（有无编造信息）
2. 回复是否回答了客户问题？
3. 引用是否准确？
4. 有无遗漏重要信息？

审核结果格式（JSON）：
{{
  "pass": true/false,
  "issues": ["问题1", "问题2"],
  "suggestions": ["建议1", "建议2"]
}}"""

            try:
                messages = [
                    {"role": "system", "content": "你是质量审核专家，负责审核客服回复质量。"},
                    {"role": "user", "content": critique_prompt},
                ]
                
                response = _call_llm(
                    messages=messages,
                    base_url=self._base_url,
                    api_key=self._api_key,
                    model=self._model,
                    timeout=self._timeout,
                    max_tokens=512,
                    temperature=0.3,  # Low temperature for consistent critique
                )
                
                critique = _extract_json(response)
                
                if not critique:
                    logger.warning("DraftAgent: failed to parse critique response")
                    break
                
                # If critique passes, return original draft
                if critique.get("pass", False):
                    logger.info("DraftAgent: self-reflection passed (revision %d)", revision)
                    return draft_result
                
                # If critique fails, revise the draft
                issues = critique.get("issues", [])
                suggestions = critique.get("suggestions", [])
                
                logger.info(
                    "DraftAgent: self-reflection found issues (revision %d): %s",
                    revision,
                    issues,
                )
                
                # Ask LLM to revise based on critique
                revise_prompt = f"""你是一名客服专家。请根据审核意见修改回复草稿。

客户问题：{normalized_text}
问题类型：{issue_type}

检索到的证据：
{evidence_summary}

原回复草稿：
{draft_text}

审核发现的问题：
{chr(10).join(f"- {issue}" for issue in issues)}

修改建议：
{chr(10).join(f"- {suggestion}" for suggestion in suggestions)}

请修改回复，确保：
1. 基于证据，不编造信息
2. 回答客户问题
3. 引用准确

修改后的回复格式（JSON）：
{{
  "draft_text": "修改后的回复内容",
  "cited_evidence_ids": ["证据ID1", "证据ID2"],
  "confidence": 0.8,
  "unsupported_claims": [],
  "missing_information": [],
  "safety_notes": []
}}"""

                messages = [
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": revise_prompt},
                ]
                
                response = _call_llm(
                    messages=messages,
                    base_url=self._base_url,
                    api_key=self._api_key,
                    model=self._model,
                    timeout=self._timeout,
                    max_tokens=1024,
                    temperature=self._temperature,
                )
                
                revised = _extract_json(response)
                
                if revised and revised.get("draft_text"):
                    draft_result = revised
                    draft_text = revised["draft_text"]
                    logger.info("DraftAgent: draft revised (revision %d)", revision)
                else:
                    logger.warning("DraftAgent: revision failed, keeping original")
                    break
                    
            except Exception as e:
                logger.error("DraftAgent: self-reflection failed: %s", e)
                break
        
        return draft_result

    def _skill_reflect(
        self,
        result: DraftReply,
        issue_type: str,
        flags: list[str],
    ) -> DraftReply:
        """Apply skill-based reflection to the draft.

        Loads relevant skills, checks the draft against best practices,
        and appends suggestions to safety_notes if issues are found.
        This is optional — failures are silently absorbed.
        """
        try:
            library = load_skill_library()
            skills = select_relevant_skills(library, issue_type, flags)
            if not skills:
                result.reflection_passed = None
                result.reflection_issues = []
                result.skill_used = None
                return result

            skill = skills[0]
            reflection = reflect_on_draft(result.draft_text, skill, flags)

            result.reflection_passed = reflection.passed
            result.reflection_issues = list(reflection.issues)
            result.skill_used = skill.skill_id

            if not reflection.passed:
                logger.info(
                    "DraftAgent: skill reflection found issues with %s: %s",
                    skill.skill_id,
                    reflection.issues,
                )
                # Append suggestions to safety notes for human reviewers
                result.safety_notes.extend(
                    f"[Skill:{skill.skill_id}] {s}" for s in reflection.suggestions
                )
                # Lower confidence slightly when skill reflection fails
                result.confidence = max(0.0, result.confidence - 0.1)

            # Increment success count for the matched skill
            skill.success_count += 1
            return result
        except Exception as e:
            logger.debug("Skill reflection skipped: %s", e)
            result.reflection_passed = None
            result.reflection_issues = []
            result.skill_used = None
            return result

    def _reformulate_search(
        self,
        normalized_text: str,
        issue_type: str,
        state: _AgentState,
    ) -> None:
        """Try a second search with reformulated keywords."""
        # Use intent-specific terms + key phrases from the message
        from ticketpilot.retrieval.query_builder import (
            _INTENT_TERMS,
            _RISK_TERMS,
        )
        from ticketpilot.schema.ticket import IntentClass, RiskFlag

        # Build alternative query using intent terms
        try:
            intent_enum = IntentClass(issue_type)
            extra_terms = _INTENT_TERMS.get(intent_enum, [])
        except ValueError:
            extra_terms = []

        # Extract key nouns from message (simple approach)
        alt_query = " ".join(extra_terms[:3]) if extra_terms else issue_type

        if alt_query not in state.search_queries_used:
            state.search_queries_used.append(alt_query)
            raw_results = _search_knowledge(alt_query)
            new_candidates = self._raw_results_to_candidates(raw_results)

            # Merge new results, deduplicating by chunk_id
            existing_ids = {c.chunk_id for c in state.evidence}
            for c in new_candidates:
                if c.chunk_id not in existing_ids:
                    state.evidence.append(c)
                    existing_ids.add(c.chunk_id)

            logger.info(
                "DraftAgent: reformulated search added %d new results",
                len(new_candidates),
            )

    def _llm_guided_search(
        self,
        normalized_text: str,
        issue_type: str,
        state: _AgentState,
    ) -> None:
        """Ask the LLM to suggest a search query when automated searches fail."""
        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"客户消息：{normalized_text}\n"
                    f"问题类型：{issue_type}\n\n"
                    "之前的搜索没有找到足够证据。请建议一个搜索关键词，"
                    "只输出JSON格式：\n"
                    '{"tool": "search_knowledge", "query": "建议的关键词"}'
                ),
            },
        ]

        try:
            response = _call_llm(
                messages=messages,
                base_url=self._base_url,
                api_key=self._api_key,
                model=self._model,
                timeout=self._timeout,
                max_tokens=256,
                temperature=self._temperature,
            )
            parsed = _extract_json(response)
            if parsed and parsed.get("tool") == "search_knowledge":
                query = parsed.get("query", "")
                if query and query not in state.search_queries_used:
                    state.search_queries_used.append(query)
                    raw_results = _search_knowledge(query)
                    state.evidence = self._raw_results_to_candidates(raw_results)
                    logger.info(
                        "DraftAgent: LLM-guided search returned %d results",
                        len(state.evidence),
                    )
        except Exception as e:
            logger.warning("DraftAgent: LLM-guided search failed: %s", e)

    def _generate_reply(
        self,
        normalized_text: str,
        issue_type: str,
        flags: list[str],
        severity: str,
        must_human_review: bool,
        evidence: list[EvidenceCandidate],
    ) -> dict[str, Any] | None:
        """Use LLM to generate a reply grounded in evidence."""

        # Format evidence for prompt
        evidence_lines: list[str] = []
        sorted_ev = sorted(evidence, key=lambda e: e.rank)[:5]
        for idx, ev in enumerate(sorted_ev, start=1):
            doc_type = ev.doc_type.value if hasattr(ev.doc_type, "value") else str(ev.doc_type)
            evidence_lines.append(f"[{idx}] ({doc_type}) {ev.content[:200]}")
        numbered_evidence = "\n".join(evidence_lines)

        # Build id mapping
        id_to_chunk: dict[int, str] = {}
        for idx, ev in enumerate(sorted_ev, start=1):
            id_to_chunk[idx] = str(ev.chunk_id)

        # Load specialized template if available
        from ticketpilot.drafting.prompt_builder import load_template
        template_content = load_template(self._template_id)
        template_section = ""
        if template_content:
            template_section = f"\n\n## 专项处理指南\n\n{template_content}"

        # Build safety instructions
        safety_lines = [
            "## 安全规则",
            "1. 回复必须基于下方证据，禁止编造信息。",
            "2. 引用证据时使用 [1]、[2] 等编号格式。",
            "3. 禁止承诺退款金额、赔偿金额、法律行动、账号变更。",
            "4. 禁止承诺解决时间线或保证特定结果。",
            "5. 只有当证据列表为空时，才建议转人工。",
            "6. 不要在回复中提及「草稿」「审核」等内部流程词。",
        ]
        if severity in ("high", "critical"):
            safety_lines.append(f"7. 本工单严重程度为「{severity}」，必须建议转人工处理。")
        if flags:
            safety_lines.append(f"8. 本工单包含风险标记：{', '.join(flags)}，回复中必须说明已升级至人工审核。")

        user_content = (
            f"用户消息：{normalized_text}\n"
            f"问题类型：{issue_type}\n"
            f"风险标记：{flags}\n"
            f"严重度：{severity}\n\n"
            f"## 可用证据\n{numbered_evidence}\n\n"
            + "\n".join(safety_lines)
            + template_section
            + "\n\n请生成回复。输出JSON格式：\n"
            '{"step": "reply", "draft_text": "回复内容", '
            '"cited_evidence_ids": ["1", "2"], "confidence": 0.8, '
            '"unsupported_claims": [], "missing_information": [], '
            '"safety_notes": []}'
        )

        messages = [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]

        try:
            response = _call_llm(
                messages=messages,
                base_url=self._base_url,
                api_key=self._api_key,
                model=self._model,
                timeout=self._timeout,
                max_tokens=self._max_tokens,
                temperature=self._temperature,
            )
            parsed = _extract_json(response)
            if parsed and "draft_text" in parsed:
                # Remap numbered citation IDs back to chunk IDs
                cited = parsed.get("cited_evidence_ids", [])
                resolved_ids: list[str] = []
                for cid in cited:
                    try:
                        idx = int(cid)
                        if idx in id_to_chunk:
                            resolved_ids.append(id_to_chunk[idx])
                        else:
                            resolved_ids.append(cid)
                    except (ValueError, TypeError):
                        resolved_ids.append(cid)
                parsed["cited_evidence_ids"] = resolved_ids
                return parsed

            # If LLM returned text but not structured JSON, wrap it
            if response and not parsed:
                return {
                    "step": "reply",
                    "draft_text": response.strip(),
                    "cited_evidence_ids": [
                        str(ev.chunk_id) for ev in sorted_ev[:3]
                    ],
                    "confidence": 0.5,
                    "unsupported_claims": [],
                    "missing_information": [],
                    "safety_notes": ["LLM未返回结构化格式，已直接使用回复文本"],
                }
            return None

        except Exception as e:
            logger.error("DraftAgent: reply generation failed: %s", e)
            return None

    def _verify_reply(
        self,
        draft_result: dict[str, Any],
        evidence: list[EvidenceCandidate],
        flags: list[str],
        must_human_review: bool,
    ) -> DraftReply:
        """Verify the generated reply and build a DraftReply.

        Checks:
        - draft_text is non-empty
        - cited evidence IDs are valid
        - presence of risk flags and severity triggers
        """
        draft_text = draft_result.get("draft_text", "")
        cited_ids = draft_result.get("cited_evidence_ids", [])
        confidence = draft_result.get("confidence", 0.5)
        unsupported = draft_result.get("unsupported_claims", [])
        missing = draft_result.get("missing_information", [])
        safety_notes = draft_result.get("safety_notes", [])

        # Clamp confidence
        try:
            confidence = max(0.0, min(1.0, float(confidence)))
        except (ValueError, TypeError):
            confidence = 0.5

        # Build citations from evidence
        evidence_by_id = {str(e.chunk_id): e for e in evidence}
        citations: list[Citation] = []
        valid_cited_ids: list[str] = []
        for cid in cited_ids:
            cid_str = str(cid)
            if cid_str in evidence_by_id:
                ev = evidence_by_id[cid_str]
                citations.append(
                    Citation(
                        chunk_id=ev.chunk_id,
                        doc_id=ev.doc_id,
                        doc_type=ev.doc_type,
                        source_table=getattr(ev, "source_table", ""),
                        source_id=getattr(ev, "source_id", ev.doc_id),
                        evidence_excerpt=ev.content[:200],
                        claim_supported=True,
                    )
                )
                valid_cited_ids.append(cid_str)

        # If no valid citations but we have evidence, add top evidence
        if not citations and evidence:
            sorted_ev = sorted(evidence, key=lambda e: e.rank)[:3]
            for ev in sorted_ev:
                citations.append(
                    Citation(
                        chunk_id=ev.chunk_id,
                        doc_id=ev.doc_id,
                        doc_type=ev.doc_type,
                        source_table=getattr(ev, "source_table", ""),
                        source_id=getattr(ev, "source_id", ev.doc_id),
                        evidence_excerpt=ev.content[:200],
                        claim_supported=True,
                    )
                )
                valid_cited_ids.append(str(ev.chunk_id))

        # Empty draft text fallback
        if not draft_text.strip():
            return self._build_fallback(
                reason="empty_draft",
                flags=flags,
                must_human_review=True,
            )

        # Determine review requirements
        needs_review = must_human_review or bool(flags) or bool(unsupported)

        escalation_reason: str | None = None
        if needs_review:
            if flags:
                escalation_reason = f"risk_flags: {', '.join(flags)}"
            elif must_human_review:
                escalation_reason = "risk_assessment_requires_review"
            elif unsupported:
                escalation_reason = "unsupported_claims_detected"

        if flags:
            safety_notes.append(f"工单含风险标记：{', '.join(flags)}，需人工审核")

        # Build generation trace for debugging
        trace = {
            "agent_iterations": _MAX_ITERATIONS,
            "search_queries": getattr(self, "_last_search_queries", []),
            "evidence_count": len(evidence),
            "cited_count": len(valid_cited_ids),
        }

        return DraftReply(
            ticket_id="",
            draft_text=draft_text,
            citations=citations,
            evidence_used=citations,
            unsupported_claims=unsupported,
            missing_information=missing,
            confidence=confidence,
            must_human_review=needs_review,
            provider_id="draft_agent",
            escalation_reason=escalation_reason,
            safety_notes=safety_notes,
            cited_evidence_ids=valid_cited_ids,
            generation_trace=trace,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _raw_results_to_candidates(
        raw_results: list[dict[str, Any]],
    ) -> list[EvidenceCandidate]:
        """Convert raw search result dicts to EvidenceCandidate objects."""
        candidates: list[EvidenceCandidate] = []
        for i, r in enumerate(raw_results):
            try:
                candidates.append(
                    EvidenceCandidate(
                        chunk_id=UUID(r["chunk_id"]),
                        doc_id=UUID(r["doc_id"]),
                        doc_type=DocType(r["doc_type"]),
                        source_id=UUID(r.get("source_id", r["doc_id"])),
                        source_table=r.get("source_table", ""),
                        content=r.get("content", ""),
                        score=r.get("score", 0.0),
                        rank=r.get("rank", i + 1),
                        title=r.get("title"),
                    )
                )
            except (KeyError, ValueError) as e:
                logger.warning("DraftAgent: skipping malformed result: %s", e)
        return candidates

    @staticmethod
    def _build_fallback(
        reason: str,
        flags: list[str],
        must_human_review: bool,
        error_msg: str | None = None,
    ) -> DraftReply:
        """Build a safe fallback DraftReply when the agent cannot proceed."""
        safety_notes: list[str] = []
        if flags:
            safety_notes.append(f"工单含风险标记：{', '.join(flags)}，需人工审核")
        if error_msg:
            safety_notes.append(f"Agent错误：{error_msg}")

        escalation_reason: str | None = None
        if flags:
            escalation_reason = f"risk_flags: {', '.join(flags)}"
        elif must_human_review:
            escalation_reason = "risk_assessment_requires_review"
        else:
            escalation_reason = "agent_fallback"

        return DraftReply(
            ticket_id="",
            draft_text=SAFE_FALLBACK_TEXT,
            citations=[],
            evidence_used=[],
            unsupported_claims=["Agent无法生成有依据的回复"],
            missing_information=["未找到相关证据"],
            confidence=0.0,
            must_human_review=True,
            fallback_reason=reason,
            provider_id="draft_agent",
            escalation_reason=escalation_reason,
            safety_notes=safety_notes,
            cited_evidence_ids=[],
        )
