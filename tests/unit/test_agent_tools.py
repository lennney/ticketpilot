"""Unit tests for Agent tool wrappers (Batch 2)."""

from datetime import datetime
from unittest.mock import patch

import pytest

from ticketpilot.agent.tools import (
    _parse_intent,
    _parse_risk_flags,
    assess_risk_tool,
    classify_ticket_tool,
    create_default_tool_registry,
    generate_draft_tool,
    normalize_ticket_tool,
    retrieve_evidence_tool,
)
from ticketpilot.schema.ticket import (
    ClassificationResult,
    IntentClass,
    NormalizedTicket,
    RawTicket,
    RiskFlag,
)


# ---------------------------------------------------------------------------
# _parse_intent / _parse_risk_flags helpers
# ---------------------------------------------------------------------------


class TestParseIntent:
    def test_passthrough_enum(self):
        assert _parse_intent(IntentClass.REFUND) is IntentClass.REFUND

    def test_from_valid_string(self):
        assert _parse_intent("refund") == IntentClass.REFUND

    def test_from_other_string(self):
        assert _parse_intent("complaint") == IntentClass.COMPLAINT

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError, match="invalid intent"):
            _parse_intent("not_an_intent")


class TestParseRiskFlags:
    def test_passthrough_set_of_enums(self):
        s = {RiskFlag.COMPLAINT_RISK, RiskFlag.LEGAL_RISK}
        result = _parse_risk_flags(s)
        assert result == s

    def test_from_list_of_strings(self):
        result = _parse_risk_flags(["complaint_risk", "legal_risk"])
        assert result == {RiskFlag.COMPLAINT_RISK, RiskFlag.LEGAL_RISK}

    def test_from_list_of_enums(self):
        result = _parse_risk_flags([RiskFlag.PRIVACY_RISK])
        assert result == {RiskFlag.PRIVACY_RISK}

    def test_invalid_string_raises(self):
        with pytest.raises(ValueError, match="invalid risk_flag"):
            _parse_risk_flags(["complaint_risk", "bogus_flag"])


# ---------------------------------------------------------------------------
# Tool wrapper functions
# ---------------------------------------------------------------------------


class TestNormalizeTicketTool:
    def test_calls_intake_pipeline_and_returns_dict(self):
        with patch("ticketpilot.agent.tools.intake_pipeline") as mock_pipeline:
            mock_pipeline.return_value = NormalizedTicket(
                text="hello world",
                language="zh",
                cleaned_at=datetime(2026, 1, 1),
            )
            raw = RawTicket(
                original_text="hello",
                submitted_at=datetime(2026, 1, 1),
            )
            result = normalize_ticket_tool({"raw_ticket": raw})

        assert result["text"] == "hello world"
        assert result["language"] == "zh"
        mock_pipeline.assert_called_once_with(raw)

    def test_accepts_dict_raw_ticket(self):
        with patch("ticketpilot.agent.tools.intake_pipeline") as mock_pipeline:
            mock_pipeline.return_value = NormalizedTicket(
                text="dict input",
                language="zh",
                cleaned_at=datetime(2026, 1, 1),
            )
            result = normalize_ticket_tool(
                {
                    "raw_ticket": {
                        "original_text": "dict input",
                        "submitted_at": "2026-01-01T00:00:00",
                    },
                }
            )
        assert result["text"] == "dict input"


class TestClassifyTicketTool:
    def test_calls_classifier(self):
        with patch("ticketpilot.agent.tools.IntentClassifier") as MockClassifier:
            instance = MockClassifier.return_value
            instance.classify.return_value = ClassificationResult(
                intent=IntentClass.REFUND,
                confidence=0.9,
                classified_at=datetime(2026, 1, 1),
            )
            result = classify_ticket_tool({"normalized_text": "我要退款"})

        assert result["intent"] == "refund"
        assert result["confidence"] == 0.9
        instance.classify.assert_called_once_with("我要退款")


class TestAssessRiskTool:
    def test_calls_assessor(self):
        with patch("ticketpilot.agent.tools.RiskAssessor") as MockAssessor:
            instance = MockAssessor.return_value
            instance.assess.return_value = MagicRiskAssessment(
                flags={RiskFlag.LOW_CONFIDENCE},
                severity="low",
                must_human_review=False,
                assessed_at="2026-01-01T00:00:00",
            )
            nt = NormalizedTicket(
                text="test",
                language="zh",
                cleaned_at=datetime(2026, 1, 1),
            )
            cl = ClassificationResult(
                intent=IntentClass.OTHER,
                confidence=0.5,
                classified_at=datetime(2026, 1, 1),
            )
            result = assess_risk_tool(
                {
                    "normalized_ticket": nt,
                    "classification": cl,
                }
            )

        assert "severity" in result
        assert result["flags"] == ["low_confidence"]

    def test_accepts_dict_inputs(self):
        with patch("ticketpilot.agent.tools.RiskAssessor") as MockAssessor:
            instance = MockAssessor.return_value
            instance.assess.return_value = MagicRiskAssessment(
                flags=set(),
                severity="low",
                must_human_review=False,
                assessed_at="2026-01-01T00:00:00",
            )
            result = assess_risk_tool(
                {
                    "normalized_ticket": {
                        "text": "test",
                        "language": "zh",
                        "cleaned_at": "2026-01-01T00:00:00",
                    },
                    "classification": {
                        "intent": "other",
                        "confidence": 0.5,
                        "classified_at": "2026-01-01T00:00:00",
                    },
                }
            )
        assert result["severity"] == "low"


class MagicRiskAssessment:
    """Stand-in because RiskAssessment uses set[RiskFlag] and model_validate
    has issues with set ordering in JSON mode. We only need model_dump(mode='json')."""

    def __init__(self, flags, severity, must_human_review, assessed_at):
        self.flags = flags
        self.severity = severity
        self.must_human_review = must_human_review
        self.assessed_at = assessed_at

    def model_dump(self, mode="json"):
        return {
            "flags": sorted(
                [f.value if hasattr(f, "value") else f for f in self.flags]
            ),
            "severity": self.severity,
            "must_human_review": self.must_human_review,
            "assessed_at": self.assessed_at,
        }


class TestRetrieveEvidenceTool:
    def test_calls_retrieve_evidence(self):
        with patch("ticketpilot.agent.tools.retrieve_evidence") as mock_re:
            mock_re.return_value = ([], MagicRetrievalTrace())
            result = retrieve_evidence_tool(
                {
                    "normalized_text": "退款问题",
                    "intent": "refund",
                    "risk_flags": ["complaint_risk"],
                }
            )

        assert result["evidence_count"] == 0
        assert "evidence_candidates" in result
        assert "retrieval_trace" in result

    def test_serializes_evidence_list(self):
        with patch("ticketpilot.agent.tools.retrieve_evidence") as mock_re:
            mock_re.return_value = (
                [MagicEvidenceCandidate(1)],
                MagicRetrievalTrace(),
            )
            result = retrieve_evidence_tool(
                {
                    "normalized_text": "test",
                    "intent": IntentClass.REFUND,
                    "risk_flags": {RiskFlag.COMPLAINT_RISK},
                }
            )
        assert result["evidence_count"] == 1
        assert len(result["evidence_candidates"]) == 1

    def test_passes_top_k(self):
        with patch("ticketpilot.agent.tools.retrieve_evidence") as mock_re:
            mock_re.return_value = ([], MagicRetrievalTrace())
            retrieve_evidence_tool(
                {
                    "normalized_text": "x",
                    "intent": "refund",
                    "risk_flags": [],
                    "top_k": 5,
                }
            )
            _name, args, _kwargs = mock_re.mock_calls[0]
            assert mock_re.call_args[1]["top_k"] == 5

    def test_invalid_intent_raises(self):
        with pytest.raises(ValueError, match="invalid intent"):
            retrieve_evidence_tool(
                {
                    "normalized_text": "x",
                    "intent": "bogus_intent",
                    "risk_flags": [],
                }
            )

    def test_invalid_risk_flag_raises(self):
        with pytest.raises(ValueError, match="invalid risk_flag"):
            retrieve_evidence_tool(
                {
                    "normalized_text": "x",
                    "intent": "refund",
                    "risk_flags": ["not_a_flag"],
                }
            )


class MagicEvidenceCandidate:
    def __init__(self, rank):
        self.rank = rank

    def model_dump(self, mode="json"):
        return {"rank": self.rank, "content": "ev", "score": 1.0}


class MagicRetrievalTrace:
    def model_dump(self, mode="json"):
        return {"query": "test", "top_k": 10}


class TestGenerateDraftTool:
    def test_calls_generate_draft(self):
        with patch("ticketpilot.agent.tools.generate_draft") as mock_gd:
            mock_gd.return_value = MagicDraftReply()
            result = generate_draft_tool(
                {
                    "ticket_output": MagicTicketOutput(),
                }
            )
        assert "draft_text" in result
        assert result["draft_text"] == "mock draft"

    def test_accepts_dict_ticket_output(self):
        with patch("ticketpilot.agent.tools.generate_draft") as mock_gd:
            mock_gd.return_value = MagicDraftReply()
            result = generate_draft_tool(
                {
                    "ticket_output": {
                        "ticket_id": "t1",
                        "raw_ticket": {
                            "original_text": "test",
                            "submitted_at": "2026-01-01T00:00:00",
                        },
                        "normalized_ticket": {
                            "text": "test",
                            "language": "zh",
                            "cleaned_at": "2026-01-01T00:00:00",
                        },
                        "classification": {
                            "intent": "other",
                            "confidence": 0.5,
                            "classified_at": "2026-01-01T00:00:00",
                        },
                        "risk_assessment": {
                            "flags": [],
                            "severity": "low",
                            "must_human_review": False,
                            "assessed_at": "2026-01-01T00:00:00",
                        },
                        "output_at": "2026-01-01T00:00:00",
                    },
                }
            )
        assert result["draft_text"] == "mock draft"


class MagicDraftReply:
    def model_dump(self, mode="json"):
        return {
            "ticket_id": "t1",
            "draft_text": "mock draft",
            "citations": [],
            "evidence_used": [],
            "unsupported_claims": [],
            "missing_information": [],
            "confidence": 0.8,
            "must_human_review": False,
        }


class MagicTicketOutput:
    ticket_id = "t1"


# ---------------------------------------------------------------------------
# Default registry
# ---------------------------------------------------------------------------


class TestDefaultToolRegistry:
    def test_contains_exactly_six_tools(self):
        registry = create_default_tool_registry()
        assert len(registry.list_names()) == 6

    def test_expected_names(self):
        registry = create_default_tool_registry()
        assert registry.list_names() == [
            "normalize_ticket",
            "classify_ticket",
            "assess_risk",
            "retrieve_evidence",
            "generate_draft",
            "request_human_input",
        ]

    def test_each_tool_has_valid_spec(self):
        registry = create_default_tool_registry()
        for spec in registry.list_specs():
            assert spec.name
            assert spec.description
            assert spec.risk_level in ("low", "medium", "high")

    def test_each_tool_has_non_empty_description(self):
        registry = create_default_tool_registry()
        for spec in registry.list_specs():
            assert len(spec.description) > 10

    def test_risk_levels_match_expected(self):
        registry = create_default_tool_registry()
        expected = {
            "normalize_ticket": "low",
            "classify_ticket": "low",
            "assess_risk": "medium",
            "retrieve_evidence": "medium",
            "generate_draft": "high",
            "request_human_input": "low",
        }
        for spec in registry.list_specs():
            assert spec.risk_level == expected[spec.name], spec.name

    def test_default_registry_call_works(self):
        registry = create_default_tool_registry()
        # Each tool's handler is the actual wrapper function, so calling
        # with valid data invokes the real wrapper which in turn calls
        # the real pipeline. We monkeypatch the underlying pipeline
        # and verify the wrapper chain works.
        with patch("ticketpilot.agent.tools.intake_pipeline") as mock_p:
            mock_p.return_value = NormalizedTicket(
                text="m",
                language="zh",
                cleaned_at=datetime(2026, 1, 1),
            )
            result = registry.call(
                "normalize_ticket",
                {
                    "raw_ticket": {
                        "original_text": "m",
                        "submitted_at": "2026-01-01T00:00:00",
                    },
                },
            )
        assert result["text"] == "m"

    def test_no_network_or_llm_calls(self):
        """Verification: default tools only wrap local deterministic logic."""
        registry = create_default_tool_registry()
        names = registry.list_names()
        assert len(names) == 6
        # All handlers must be local functions (no requests/openai/etc.)
        import inspect

        for name in names:
            handler = registry.get(name).handler
            assert callable(handler)
            source = inspect.getsource(handler)
            # Quick check: no obvious network/LLM imports in the handler source
            assert "requests" not in source
            assert "openai" not in source
