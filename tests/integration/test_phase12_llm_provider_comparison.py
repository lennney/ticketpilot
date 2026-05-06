"""Integration tests for Phase 12 LLM Provider Comparison Runner.

Tests the comparison script execution without requiring a real LLM API.
"""

import json
import subprocess
import sys
from pathlib import Path


# Path to the runner script
RUNNER_SCRIPT = Path(__file__).parent.parent.parent / "scripts" / "run_phase12_llm_provider_comparison.py"
FIXTURES_PATH = Path(__file__).parent.parent / "fixtures" / "phase12_draft_comparison_cases.json"


class TestPhase12RunnerIntegration:
    """Integration tests for the comparison runner."""

    def test_runner_help_flag(self):
        """Test that runner accepts --help flag."""
        result = subprocess.run(
            [sys.executable, str(RUNNER_SCRIPT), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Phase 12 LLM Provider Comparison" in result.stdout

    def test_runner_with_limit(self, tmp_path):
        """Test runner execution with limited cases."""
        result = subprocess.run(
            [sys.executable, str(RUNNER_SCRIPT), "--limit", "3", "--output-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Loaded 25 test cases" in result.stdout
        assert "Running FakeLLMProvider baseline" in result.stdout
        assert "/3 successful" in result.stdout

    def test_runner_generates_json_output(self, tmp_path):
        """Test that runner generates JSON results file."""
        result = subprocess.run(
            [sys.executable, str(RUNNER_SCRIPT), "--limit", "2", "--output-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        json_files = list(tmp_path.glob("phase12_llm_provider_comparison_*.json"))
        assert len(json_files) == 1

        with open(json_files[0], encoding="utf-8") as f:
            data = json.load(f)

        assert "fake_results" in data
        assert data["fake_results"]["total_cases"] == 2
        assert data["fake_results"]["successful"] == 2

    def test_runner_generates_markdown_report(self, tmp_path):
        """Test that runner generates markdown report."""
        result = subprocess.run(
            [sys.executable, str(RUNNER_SCRIPT), "--limit", "2", "--output-dir", str(tmp_path)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0

        md_files = list(tmp_path.glob("phase12_llm_provider_comparison_report_*.md"))
        assert len(md_files) == 1

        with open(md_files[0], encoding="utf-8") as f:
            content = f.read()

        assert "Phase 12" in content
        assert "FakeLLMProvider" in content
        assert "local demo" in content.lower()

    def test_fixtures_file_exists_and_valid(self):
        """Test that fixture file exists and is valid JSON."""
        assert FIXTURES_PATH.exists(), f"Fixtures not found: {FIXTURES_PATH}"

        with open(FIXTURES_PATH, encoding="utf-8") as f:
            fixtures = json.load(f)

        assert isinstance(fixtures, list)
        assert len(fixtures) >= 25

        # Check structure
        required_keys = {"case_id", "scenario", "normalized_text", "issue_type", "risk_flags"}
        for fixture in fixtures[:3]:
            assert required_keys.issubset(fixture.keys()), f"Missing keys in fixture: {fixture}"

    def test_runner_handles_missing_fixtures(self, tmp_path):
        """Test runner behavior when fixture file is missing."""
        result = subprocess.run(
            [
                sys.executable, str(RUNNER_SCRIPT),
                "--fixtures", str(tmp_path / "nonexistent.json"),
                "--output-dir", str(tmp_path),
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "Fixture file not found" in result.stdout