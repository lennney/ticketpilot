"""Tests for CLI trigger."""

import json
import pytest
from unittest.mock import patch, MagicMock

from ticketpilot.triggers.cli import (
    parse_args,
    get_ticket_text,
    format_output,
    main,
)


class TestParseArgs:
    def test_text_arg(self):
        args = parse_args(["test ticket"])
        assert args.text == "test ticket"
        assert args.file is None
        assert args.stdin is False

    def test_file_arg(self):
        args = parse_args(["--file", "test.txt"])
        assert args.text is None
        assert args.file.name == "test.txt"
        assert args.stdin is False

    def test_stdin_arg(self):
        args = parse_args(["--stdin"])
        assert args.text is None
        assert args.file is None
        assert args.stdin is True

    def test_json_output(self):
        args = parse_args(["test", "--json"])
        assert args.json is True

    def test_pretty_output(self):
        args = parse_args(["test", "--json", "--pretty"])
        assert args.pretty is True

    def test_output_file(self):
        args = parse_args(["test", "--output", "out.json"])
        assert args.output.name == "out.json"

    def test_customer_id(self):
        args = parse_args(["test", "--customer-id", "c123"])
        assert args.customer_id == "c123"

    def test_no_input_raises(self):
        with pytest.raises(SystemExit):
            parse_args([])


class TestGetTicketText:
    def test_from_text(self):
        args = parse_args(["hello world"])
        assert get_ticket_text(args) == "hello world"

    def test_from_stdin(self, monkeypatch):
        monkeypatch.setattr("sys.stdin", MagicMock(read=lambda: "stdin text"))
        args = parse_args(["--stdin"])
        assert get_ticket_text(args) == "stdin text"

    def test_from_file(self, tmp_path):
        test_file = tmp_path / "test.txt"
        test_file.write_text("file text")
        args = parse_args(["--file", str(test_file)])
        assert get_ticket_text(args) == "file text"


class TestFormatOutput:
    def test_json_format(self):
        result = {"ticket_id": "t1", "classification": {"intent": "complaint"}}
        output = format_output(result, as_json=True)
        parsed = json.loads(output)
        assert parsed["ticket_id"] == "t1"

    def test_pretty_json(self):
        result = {"ticket_id": "t1"}
        output = format_output(result, as_json=True, pretty=True)
        assert "\n" in output

    def test_human_readable(self):
        result = {
            "ticket_id": "t1",
            "classification": {"intent": "complaint", "confidence": 0.8, "reasoning": "test"},
            "risk_assessment": {"risk_level": "medium"},
            "evidence": [],
            "draft": {"text": "reply"},
            "confidence": {"overall": 0.7, "level": "medium"},
            "degraded_response": {"strategy": "auto_send"},
        }
        output = format_output(result, as_json=False)
        assert "Ticket ID: t1" in output
        assert "Intent: complaint" in output


class TestMain:
    @patch("ticketpilot.triggers.cli.intake_risk_pipeline")
    def test_success(self, mock_pipeline):
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "ticket_id": "t1",
            "classification": {"intent": "complaint", "confidence": 0.8, "reasoning": "test"},
            "risk_assessment": {"risk_level": "medium"},
            "evidence": [],
            "draft": {"text": "reply"},
            "confidence": {"overall": 0.7, "level": "medium"},
            "degraded_response": {"strategy": "auto_send"},
        }
        mock_pipeline.return_value = mock_result

        exit_code = main(["test ticket"])
        assert exit_code == 0
        mock_pipeline.assert_called_once()

    @patch("ticketpilot.triggers.cli.intake_risk_pipeline")
    def test_json_output(self, mock_pipeline):
        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"ticket_id": "t1"}
        mock_pipeline.return_value = mock_result

        exit_code = main(["test", "--json"])
        assert exit_code == 0

    def test_empty_text(self):
        exit_code = main([""])
        assert exit_code == 1
