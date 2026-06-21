"""Tests for request_human_input tool — Factor 7."""

import pytest

from ticketpilot.agent.tools import request_human_input_tool


class TestRequestHumanInputTool:
    """Tests for request_human_input_tool."""

    def test_basic_request(self):
        """Tool returns a pause signal with question and context."""
        result = request_human_input_tool(
            {
                "question": "是否同意退款？",
                "context": {"ticket_id": "T-001", "amount": 99.0},
            }
        )

        assert result["status"] == "pause_requested"
        assert result["question"] == "是否同意退款？"
        assert result["context"]["ticket_id"] == "T-001"

    def test_with_options(self):
        """Tool accepts predefined options for the human."""
        result = request_human_input_tool(
            {
                "question": "请选择处理方式",
                "context": {"ticket_id": "T-002"},
                "options": ["approve", "reject", "escalate"],
            }
        )

        assert result["status"] == "pause_requested"
        assert result["options"] == ["approve", "reject", "escalate"]

    def test_with_urgency(self):
        """Tool accepts urgency level."""
        result = request_human_input_tool(
            {
                "question": "紧急投诉处理",
                "context": {"ticket_id": "T-003"},
                "urgency": "high",
            }
        )

        assert result["urgency"] == "high"

    def test_default_urgency(self):
        """Default urgency is medium."""
        result = request_human_input_tool(
            {
                "question": "普通审核",
                "context": {},
            }
        )

        assert result["urgency"] == "medium"

    def test_missing_question_raises(self):
        """Question is required."""
        with pytest.raises(KeyError):
            request_human_input_tool({"context": {}})

    def test_context_preserved(self):
        """All context fields are preserved in the output."""
        context = {
            "ticket_id": "T-004",
            "confidence": 0.35,
            "evidence_count": 0,
            "risk_flags": ["complaint"],
        }
        result = request_human_input_tool(
            {
                "question": "低置信度工单",
                "context": context,
            }
        )

        assert result["context"] == context
