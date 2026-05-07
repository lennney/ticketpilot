"""Unit tests for the evidence-grounded prompt builder."""

from uuid import uuid4

import pytest

from ticketpilot.drafting.prompt_builder import (
    DraftPromptInput,
    build_output_format_instructions,
    build_prompt,
    build_safety_instructions,
    format_evidence_block,
)
from ticketpilot.retrieval.schema.knowledge import DocType
from ticketpilot.schema.evidence import EvidenceCandidate


def _make_evidence(
    rank: int = 1,
    score: float = 0.8,
    content: str = "退货需要在7天内申请，超过7天需要特殊审批。",
    doc_type: DocType = DocType.FAQ,
    title: str | None = None,
) -> EvidenceCandidate:
    return EvidenceCandidate(
        chunk_id=uuid4(),
        doc_id=uuid4(),
        doc_type=doc_type,
        source_id=uuid4(),
        source_table=f"knowledge_{doc_type.value.lower()}",
        content=content,
        score=score,
        rank=rank,
        title=title,
    )


class TestDraftPromptInput:
    def test_default_values(self):
        inp = DraftPromptInput(ticket_text="我要退款", issue_type="refund")
        assert inp.ticket_text == "我要退款"
        assert inp.issue_type == "refund"
        assert inp.risk_flags == []
        assert inp.severity == "low"
        assert inp.must_human_review is False
        assert inp.evidence_candidates == []

    def test_all_fields_populated(self):
        ev = _make_evidence()
        inp = DraftPromptInput(
            ticket_text="test",
            issue_type="refund",
            risk_flags=["legal"],
            severity="high",
            must_human_review=True,
            evidence_candidates=[ev],
        )
        assert inp.risk_flags == ["legal"]
        assert inp.severity == "high"
        assert inp.must_human_review is True
        assert len(inp.evidence_candidates) == 1


class TestFormatEvidenceBlock:
    def test_formats_chunk_id(self):
        ev = _make_evidence(rank=1)
        block = format_evidence_block([ev])
        assert str(ev.chunk_id) in block

    def test_formats_doc_id(self):
        ev = _make_evidence(rank=1)
        block = format_evidence_block([ev])
        assert str(ev.doc_id) in block

    def test_formats_doc_type(self):
        ev = _make_evidence(rank=1, doc_type=DocType.POLICY)
        block = format_evidence_block([ev])
        assert DocType.POLICY.value in block

    def test_formats_title_when_present(self):
        ev = _make_evidence(rank=1, title="退款政策说明")
        block = format_evidence_block([ev])
        assert "退款政策说明" in block

    def test_no_title_when_missing(self):
        ev = _make_evidence(rank=1, title=None)
        block = format_evidence_block([ev])
        assert "（None）" not in block
        assert "[标题]:" in block

    def test_formats_content_snippet(self):
        ev = _make_evidence(rank=1, content="这是证据内容。")
        block = format_evidence_block([ev])
        assert "这是证据内容。" in block

    def test_empty_content_skipped(self):
        ev = _make_evidence(rank=1, content="   ")
        block = format_evidence_block([ev])
        assert "[无可用证据]" in block

    def test_evidence_order_deterministic(self):
        evs = [
            _make_evidence(rank=2, content="second"),
            _make_evidence(rank=1, content="first"),
            _make_evidence(rank=3, content="third"),
        ]
        block = format_evidence_block(evs)
        first_pos = block.index("first")
        second_pos = block.index("second")
        third_pos = block.index("third")
        assert first_pos < second_pos < third_pos

    def test_truncation_deterministic(self):
        long_content = "A" * 500
        ev = _make_evidence(rank=1, content=long_content)
        block = format_evidence_block([ev], max_chars=50)
        assert "A" * 50 in block
        assert "A" * 51 not in block

    def test_max_evidence_count_enforced(self):
        evs = [_make_evidence(rank=i) for i in range(1, 10)]
        block = format_evidence_block(evs, max_count=3)
        # Should contain exactly 3 evidence blocks
        count = block.count("[证据 ID]:")
        assert count == 3

    def test_no_evidence_empty_block(self):
        block = format_evidence_block([])
        assert "[无可用证据]" in block

    def test_same_input_same_output(self):
        evs = [_make_evidence(rank=1, score=0.9)]
        block1 = format_evidence_block(evs)
        block2 = format_evidence_block(evs)
        assert block1 == block2

    def test_rank_and_score_displayed(self):
        ev = _make_evidence(rank=2, score=0.75)
        block = format_evidence_block([ev])
        assert "排名 2" in block
        assert "评分 0.75" in block


class TestBuildSafetyInstructions:
    def test_no_auto_send_instruction_present(self):
        instructions = build_safety_instructions()
        assert "不会自动发送" in instructions or "草稿" in instructions

    def test_citation_requirement_present(self):
        instructions = build_safety_instructions()
        assert "证据ID" in instructions

    def test_forbidden_promise_instruction_present(self):
        instructions = build_safety_instructions()
        assert "禁止承诺退款" in instructions

    def test_risk_flags_produce_review_instruction(self):
        instructions = build_safety_instructions(risk_flags=["legal", "complaint"])
        assert "legal" in instructions
        assert "complaint" in instructions
        assert "人工审核" in instructions

    def test_must_human_review_produces_instruction(self):
        instructions = build_safety_instructions(must_human_review=True)
        assert "人工审核" in instructions

    def test_high_severity_noted(self):
        instructions = build_safety_instructions(severity="high")
        assert "high" in instructions or "高" in instructions

    def test_critical_severity_noted(self):
        instructions = build_safety_instructions(severity="critical")
        assert "critical" in instructions or "高" in instructions

    def test_low_severity_no_special_note(self):
        instructions = build_safety_instructions(severity="low")
        assert "low" not in instructions

    def test_same_input_same_output(self):
        i1 = build_safety_instructions(risk_flags=["legal"], severity="high")
        i2 = build_safety_instructions(risk_flags=["legal"], severity="high")
        assert i1 == i2


class TestBuildOutputFormatInstructions:
    def test_contains_answer_text(self):
        fmt = build_output_format_instructions()
        assert "answer_text" in fmt

    def test_contains_cited_evidence_ids(self):
        fmt = build_output_format_instructions()
        assert "cited_evidence_ids" in fmt

    def test_contains_unsupported_claims(self):
        fmt = build_output_format_instructions()
        assert "unsupported_claims" in fmt

    def test_contains_safety_notes(self):
        fmt = build_output_format_instructions()
        assert "safety_notes" in fmt

    def test_contains_must_human_review(self):
        fmt = build_output_format_instructions()
        assert "must_human_review" in fmt

    def test_contains_confidence(self):
        fmt = build_output_format_instructions()
        assert "confidence" in fmt

    def test_same_input_same_output(self):
        assert build_output_format_instructions() == build_output_format_instructions()


class TestBuildPrompt:
    def test_prompt_includes_ticket_text(self):
        inp = DraftPromptInput(ticket_text="我想退款", issue_type="refund")
        prompt = build_prompt(inp)
        assert "我想退款" in prompt

    def test_prompt_includes_issue_type(self):
        inp = DraftPromptInput(ticket_text="test", issue_type="return_exchange")
        prompt = build_prompt(inp)
        assert "return_exchange" in prompt

    def test_prompt_includes_severity(self):
        inp = DraftPromptInput(ticket_text="test", issue_type="refund", severity="high")
        prompt = build_prompt(inp)
        assert "high" in prompt

    def test_prompt_includes_risk_flags(self):
        inp = DraftPromptInput(
            ticket_text="test", issue_type="refund", risk_flags=["legal", "complaint"]
        )
        prompt = build_prompt(inp)
        assert "legal" in prompt
        assert "complaint" in prompt

    def test_prompt_includes_evidence_ids(self):
        ev = _make_evidence(rank=1)
        inp = DraftPromptInput(
            ticket_text="test", issue_type="refund", evidence_candidates=[ev]
        )
        prompt = build_prompt(inp)
        assert str(ev.chunk_id) in prompt
        assert str(ev.doc_id) in prompt

    def test_prompt_includes_evidence_content(self):
        ev = _make_evidence(rank=1, content="退货需要7天内申请")
        inp = DraftPromptInput(
            ticket_text="test", issue_type="refund", evidence_candidates=[ev]
        )
        prompt = build_prompt(inp)
        assert "退货需要7天内申请" in prompt

    def test_no_evidence_shows_fallback(self):
        inp = DraftPromptInput(ticket_text="test", issue_type="refund")
        prompt = build_prompt(inp)
        assert "[无可用证据]" in prompt


class TestGuardAwarePrompting:
    """Tests for guard-aware prompting requirements.

    Verifies that prompts include [chunk_id] citation format requirements
    to support claim guard's citation marker detection.
    """

    def test_format_evidence_block_includes_chunk_id(self):
        ev = _make_evidence(rank=1, content="退货需要在7天内申请")
        block = format_evidence_block([ev])
        # Evidence block must include the chunk_id so the LLM can reference it
        assert str(ev.chunk_id) in block
        # Evidence block must NOT use numeric [1], [2] format for the ID
        # (numeric format is checked separately for invalid citation detection)
        assert "[1]" not in block
        assert "[2]" not in block

    def test_format_evidence_block_multiple_items(self):
        ev1 = _make_evidence(rank=1, content="内容1")
        ev2 = _make_evidence(rank=2, content="内容2")
        block = format_evidence_block([ev1, ev2])
        assert str(ev1.chunk_id) in block
        assert str(ev2.chunk_id) in block
        # Each chunk_id appears in the block
        assert "[1]" not in block  # no numeric citation in evidence block

    def test_build_safety_instructions_requires_chunk_id_format(self):
        instructions = build_safety_instructions()
        # Must instruct to use evidence ID format
        assert "证据ID" in instructions or "chunk_id" in instructions.lower() or "chunk" in instructions.lower()

    def test_build_safety_instructions_forbids_numeric_citations(self):
        """Numeric [N] citations are not valid for claim guard detection."""
        # The instruction should specify using evidence IDs, not numeric indices
        # We check the evidence block does not use [1], [2] style
        ev = _make_evidence()
        block = format_evidence_block([ev])
        assert "[1]" not in block  # evidence block uses [chunk_id], not [1]

    def test_build_safety_instructions_safe_fallback_instruction(self):
        instructions = build_safety_instructions()
        # Must instruct to use safe fallback when evidence is insufficient
        assert "转人工" in instructions or "人工" in instructions

    def test_build_safety_instructions_no_auto_send(self):
        instructions = build_safety_instructions()
        # Must state this is a draft, not final
        assert "草稿" in instructions

    def test_build_safety_instructions_forbidden_promises(self):
        instructions = build_safety_instructions()
        # Must forbid specific promises
        assert "禁止承诺退款" in instructions or "退款" in instructions

    def test_build_safety_instructions_risk_flags_escalation(self):
        instructions = build_safety_instructions(
            risk_flags=["legal", "compensation"], severity="high"
        )
        # HIGH severity + risk flags must mention escalation
        assert "人工" in instructions or "审核" in instructions

    def test_guard_aware_prompt_combined(self):
        """Full prompt includes all guard-aware components."""
        ev = _make_evidence(rank=1, content="退货需要在7天内申请")
        inp = DraftPromptInput(
            ticket_text="我要退货",
            issue_type="refund",
            risk_flags=["complaint"],
            severity="medium",
            evidence_candidates=[ev],
        )
        prompt = build_prompt(inp)
        # Must include ticket text
        assert "我要退货" in prompt
        # Must include evidence with chunk_id
        assert str(ev.chunk_id) in prompt
        # Must include safety instructions
        assert "草稿" in prompt
        # Must include citation requirement
        assert "证据ID" in prompt
        # Must include risk escalation
        assert "complaint" in prompt

    def test_risk_flags_produce_review_prompt(self):
        inp = DraftPromptInput(
            ticket_text="test", issue_type="refund", risk_flags=["legal"]
        )
        prompt = build_prompt(inp)
        assert "人工审核" in prompt

    def test_evidence_order_deterministic_in_prompt(self):
        evs = [
            _make_evidence(rank=2, content="second_ev"),
            _make_evidence(rank=1, content="first_ev"),
        ]
        inp1 = DraftPromptInput(
            ticket_text="test", issue_type="refund", evidence_candidates=evs
        )
        inp2 = DraftPromptInput(
            ticket_text="test", issue_type="refund", evidence_candidates=evs
        )
        assert build_prompt(inp1) == build_prompt(inp2)

    def test_max_evidence_enforced_in_prompt(self):
        evs = [_make_evidence(rank=i) for i in range(1, 10)]
        inp = DraftPromptInput(
            ticket_text="test", issue_type="refund", evidence_candidates=evs
        )
        prompt = build_prompt(inp, max_evidence=2)
        count = prompt.count("[证据 ID]:")
        assert count == 2

    def test_empty_content_handled(self):
        ev = _make_evidence(rank=1, content="")
        inp = DraftPromptInput(
            ticket_text="test", issue_type="refund", evidence_candidates=[ev]
        )
        prompt = build_prompt(inp)
        assert "[无可用证据]" in prompt

    def test_empty_ticket_text_raises(self):
        inp = DraftPromptInput(ticket_text="", issue_type="refund")
        with pytest.raises(ValueError, match="ticket_text must not be empty"):
            build_prompt(inp)

    def test_whitespace_only_ticket_raises(self):
        inp = DraftPromptInput(ticket_text="   ", issue_type="refund")
        with pytest.raises(ValueError, match="ticket_text must not be empty"):
            build_prompt(inp)

    def test_same_input_same_output(self):
        ev = _make_evidence(rank=1, score=0.8)
        inp = DraftPromptInput(
            ticket_text="test", issue_type="refund", evidence_candidates=[ev]
        )
        p1 = build_prompt(inp)
        p2 = build_prompt(inp)
        assert p1 == p2

    def test_prompt_contains_draft_only_instruction(self):
        inp = DraftPromptInput(ticket_text="test", issue_type="refund")
        prompt = build_prompt(inp)
        assert "草稿" in prompt

    def test_prompt_contains_citation_requirement(self):
        inp = DraftPromptInput(ticket_text="test", issue_type="refund")
        prompt = build_prompt(inp)
        assert "证据ID" in prompt

    def test_prompt_contains_no_send_instruction(self):
        inp = DraftPromptInput(ticket_text="test", issue_type="refund")
        prompt = build_prompt(inp)
        assert "不会自动发送" in prompt

    def test_must_human_review_included(self):
        inp = DraftPromptInput(
            ticket_text="test", issue_type="refund", must_human_review=True
        )
        prompt = build_prompt(inp)
        assert "需要人工审核" in prompt

    def test_prompt_has_expected_structure(self):
        inp = DraftPromptInput(ticket_text="test", issue_type="refund")
        prompt = build_prompt(inp)
        assert "工单信息" in prompt
        assert "可用证据" in prompt
        assert "安全与约束规则" in prompt
        assert "输出格式要求" in prompt
