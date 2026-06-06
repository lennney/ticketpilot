"""Tests for error compaction — Factor 9."""

from ticketpilot.agent.error_compaction import compact_error, compact_errors


class TestCompactError:
    """Tests for compact_error function."""

    def test_basic_compaction(self):
        """Compacts error type + message + context."""
        result = compact_error(ConnectionError("Connection refused"), "retrieval")
        assert result == "ConnectionError: Connection refused (context: retrieval)"

    def test_value_error(self):
        """Works with ValueError."""
        result = compact_error(ValueError("empty text after normalization"), "intake")
        assert "ValueError" in result
        assert "empty text" in result
        assert "intake" in result

    def test_truncation(self):
        """Long messages are truncated to max_len."""
        long_msg = "x" * 500
        result = compact_error(RuntimeError(long_msg), "test", max_len=50)
        assert len(result) < 100
        assert "xxxxx" in result

    def test_empty_message(self):
        """Works with empty error message."""
        result = compact_error(Exception(""), "step1")
        assert "Exception" in result
        assert "step1" in result


class TestCompactErrors:
    """Tests for compact_errors function."""

    def test_multiple_errors(self):
        """Compacts a list of errors."""
        errors = [
            (ConnectionError("timeout"), "retrieval"),
            (ValueError("bad input"), "intake"),
        ]
        results = compact_errors(errors)
        assert len(results) == 2
        assert "ConnectionError" in results[0]
        assert "ValueError" in results[1]

    def test_empty_list(self):
        """Empty list returns empty list."""
        assert compact_errors([]) == []
