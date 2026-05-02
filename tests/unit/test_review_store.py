"""Unit tests for ReviewStore JSONL persistence."""

import os
import tempfile

from ticketpilot.review.schemas import ReviewAction, ReviewDecision
from ticketpilot.review.store import ReviewStore


class TestReviewStore:
    """ReviewStore JSONL persistence validation."""

    def test_save_and_load_single_decision(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            decision = ReviewDecision(
                ticket_id="ticket-001",
                ticket_text="我要退款",
                action=ReviewAction.APPROVE,
                original_draft_text="您好，关于退款问题...",
            )
            store.save(decision)
            loaded = store.load_all()
            assert len(loaded) == 1
            assert loaded[0].ticket_id == "ticket-001"
            assert loaded[0].action == ReviewAction.APPROVE

    def test_accumulates_multiple_decisions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            for i in range(3):
                store.save(
                    ReviewDecision(
                        ticket_id=f"ticket-{i:03d}",
                        ticket_text=f"测试{i}",
                        action=ReviewAction.APPROVE,
                        original_draft_text=f"草稿{i}",
                    )
                )
            loaded = store.load_all()
            assert len(loaded) == 3
            assert loaded[0].ticket_id == "ticket-000"
            assert loaded[1].ticket_id == "ticket-001"
            assert loaded[2].ticket_id == "ticket-002"

    def test_empty_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "empty.jsonl")
            store = ReviewStore(path)
            loaded = store.load_all()
            assert loaded == []

    def test_nonexistent_file_returns_empty_list(self):
        store = ReviewStore("/tmp/nonexistent_dir_xyz/reviews.jsonl")
        loaded = store.load_all()
        assert loaded == []

    def test_roundtrip_preserves_all_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            original = ReviewDecision(
                ticket_id="ticket-010",
                ticket_text="退货",
                action=ReviewAction.EDIT,
                original_draft_text="您好...",
                edited_text="您好，已为您处理退货。",
                decision_reason="补充了退货说明",
                confidence=0.75,
                had_unsupported_claims=True,
                was_high_risk=False,
                intent="refund",
                risk_flags=["COMPENSATION_RISK"],
                citations_summary=[{"chunk_id": "abc", "doc_type": "FAQ"}],
                evidence_used_count=1,
                reviewer_label="reviewer-li",
            )
            store.save(original)
            loaded = store.load_all()
            assert len(loaded) == 1
            restored = loaded[0]
            assert restored.review_id == original.review_id
            assert restored.ticket_id == original.ticket_id
            assert restored.ticket_text == original.ticket_text
            assert restored.action == original.action
            assert restored.edited_text == original.edited_text
            assert restored.decision_reason == original.decision_reason
            assert restored.original_draft_text == original.original_draft_text
            assert restored.confidence == original.confidence
            assert restored.had_unsupported_claims == original.had_unsupported_claims
            assert restored.was_high_risk == original.was_high_risk
            assert restored.intent == original.intent
            assert restored.risk_flags == original.risk_flags
            assert restored.citations_summary == original.citations_summary
            assert restored.evidence_used_count == original.evidence_used_count
            assert restored.reviewer_label == "reviewer-li"

    def test_saves_are_append_only(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            store.save(
                ReviewDecision(
                    ticket_id="ticket-001",
                    ticket_text="测试",
                    action=ReviewAction.APPROVE,
                    original_draft_text="草稿1",
                )
            )
            store.save(
                ReviewDecision(
                    ticket_id="ticket-002",
                    ticket_text="测试2",
                    action=ReviewAction.REJECT,
                    original_draft_text="草稿2",
                    decision_reason="不采纳",
                )
            )
            loaded = store.load_all()
            assert len(loaded) == 2
            assert loaded[0].ticket_id == "ticket-001"
            assert loaded[1].ticket_id == "ticket-002"

    def test_invalid_jsonl_line_skipped(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            decision = ReviewDecision(
                ticket_id="ticket-001",
                ticket_text="测试",
                action=ReviewAction.APPROVE,
                original_draft_text="草稿",
            )
            store.save(decision)
            # Append an invalid line
            with open(path, "a", encoding="utf-8") as f:
                f.write("not valid json\n")
            # Append another valid decision
            store.save(
                ReviewDecision(
                    ticket_id="ticket-002",
                    ticket_text="测试2",
                    action=ReviewAction.REJECT,
                    original_draft_text="草稿2",
                )
            )
            loaded = store.load_all()
            assert len(loaded) == 2
            assert loaded[0].ticket_id == "ticket-001"
            assert loaded[1].ticket_id == "ticket-002"

    def test_count(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "reviews.jsonl")
            store = ReviewStore(path)
            assert store.count() == 0
            store.save(
                ReviewDecision(
                    ticket_id="ticket-001",
                    ticket_text="测试",
                    action=ReviewAction.APPROVE,
                    original_draft_text="草稿",
                )
            )
            assert store.count() == 1
            store.save(
                ReviewDecision(
                    ticket_id="ticket-002",
                    ticket_text="测试2",
                    action=ReviewAction.ESCALATE,
                    original_draft_text="草稿2",
                )
            )
            assert store.count() == 2

    def test_store_creates_parent_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_dir = os.path.join(tmpdir, "a", "b", "c")
            path = os.path.join(nested_dir, "reviews.jsonl")
            store = ReviewStore(path)
            decision = ReviewDecision(
                ticket_id="ticket-001",
                ticket_text="测试",
                action=ReviewAction.APPROVE,
                original_draft_text="草稿",
            )
            store.save(decision)
            assert os.path.exists(path)
            loaded = store.load_all()
            assert len(loaded) == 1
