"""Tests for ticketpilot.optimizer.fixer."""

from __future__ import annotations

from typing import Any

from ticketpilot.optimizer.config import FIX_PRIORITY
from ticketpilot.optimizer.diagnostics import Diagnosis
from ticketpilot.optimizer.fixer import Fixer, FixResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_diagnosis(
    *,
    fix_type: str = "intent_keyword",
    intent: str | None = "REFUND",
    risk_flag: str | None = None,
    threshold_name: str | None = None,
    new_value: float | None = None,
    keywords: list[str] | None = None,
    affected_cases: list[str] | None = None,
) -> Diagnosis:
    """Create a Diagnosis with sensible defaults for each fix type."""
    expected: dict[str, Any] = {}
    if intent:
        expected["intent"] = intent
    if risk_flag:
        expected["risk_flag"] = risk_flag
    if threshold_name:
        expected["threshold_name"] = threshold_name
    if new_value is not None:
        expected["new_value"] = new_value

    return Diagnosis(
        type="test",
        priority=FIX_PRIORITY.get(fix_type, 5),
        affected_cases=affected_cases or ["T001", "T002"],
        expected_values=expected,
        predicted_values={},
        suggested_fix_type=fix_type,
        suggested_keywords=keywords or ["退款超时", "退款未到账"],
        fix_gain=0.007,
        description="Test diagnosis",
    )


# ---------------------------------------------------------------------------
# FixResult basics
# ---------------------------------------------------------------------------


class TestFixResult:
    def test_dataclass_fields(self) -> None:
        r = FixResult(success=True, fix_type="test", description="ok")
        assert r.success is True
        assert r.files_modified == []
        assert r.error is None

    def test_error_field(self) -> None:
        r = FixResult(success=False, fix_type="test", description="fail", error="boom")
        assert r.error == "boom"


# ---------------------------------------------------------------------------
# Fixer: dry-run mode
# ---------------------------------------------------------------------------


class TestFixerDryRun:
    def test_dry_run_intent_keyword_returns_success(self) -> None:
        fixer = Fixer(dry_run=True)
        diag = _make_diagnosis(fix_type="intent_keyword", intent="REFUND")
        result = fixer.apply_fix(diag)
        assert isinstance(result, FixResult)
        assert result.success is True
        assert "dry-run" in result.description

    def test_dry_run_confidence_threshold_returns_success(self) -> None:
        fixer = Fixer(dry_run=True)
        diag = _make_diagnosis(
            fix_type="confidence_threshold",
            threshold_name="CONFIDENCE_MEDIUM",
            new_value=0.55,
        )
        result = fixer.apply_fix(diag)
        assert result.success is True
        assert "dry-run" in result.description

    def test_dry_run_risk_keyword_returns_success(self) -> None:
        fixer = Fixer(dry_run=True)
        diag = _make_diagnosis(
            fix_type="risk_keyword",
            risk_flag="COMPLAINT_RISK",
            keywords=["举报"],
        )
        result = fixer.apply_fix(diag)
        assert result.success is True
        assert "dry-run" in result.description

    def test_dry_run_does_not_modify_files(self) -> None:
        """Ensure dry-run does not write to disk."""
        from pathlib import Path

        import ticketpilot.classification.rules as rules_mod

        assert rules_mod.__file__ is not None
        before = Path(rules_mod.__file__).read_text(encoding="utf-8")

        fixer = Fixer(dry_run=True)
        diag = _make_diagnosis(fix_type="intent_keyword", intent="REFUND")
        fixer.apply_fix(diag)

        after = Path(rules_mod.__file__).read_text(encoding="utf-8")
        assert before == after, "Dry-run should not modify the rules file"


# ---------------------------------------------------------------------------
# Fixer: unknown / missing fix type
# ---------------------------------------------------------------------------


class TestFixerEdgeCases:
    def test_missing_suggested_fix_type(self) -> None:
        fixer = Fixer(dry_run=True)
        diag = Diagnosis(
            type="unknown",
            priority=5,
            affected_cases=[],
            expected_values={},
            predicted_values={},
            suggested_fix_type="",
            suggested_keywords=[],
            fix_gain=0.0,
            description="empty fix type",
        )
        result = fixer.apply_fix(diag)
        assert result.success is False
        assert "unsupported fix type" in (result.error or "")

    def test_unsupported_fix_type(self) -> None:
        fixer = Fixer(dry_run=True)
        diag = _make_diagnosis(fix_type="reranker_weight")
        result = fixer.apply_fix(diag)
        assert result.success is False
        assert "unsupported fix type" in (result.error or "")


# ---------------------------------------------------------------------------
# Fixer: intent keyword fix (real write + rollback)
# ---------------------------------------------------------------------------


class TestFixerIntentKeywords:
    def test_add_keywords_real_write(self) -> None:
        """Write new keywords to rules.py and verify they appear."""
        from pathlib import Path
        import importlib

        fixer = Fixer(dry_run=False)
        rules_mod = importlib.import_module("ticketpilot.classification.rules")
        assert rules_mod.__file__ is not None
        rules_path = str(Path(rules_mod.__file__).resolve())
        fixer._backup_file(rules_path)

        before = Path(rules_path).read_text(encoding="utf-8")

        new_kws = ["退款超时", "退款未到账"]
        for kw in new_kws:
            assert kw not in before, f"'{kw}' already present in original"

        diag = _make_diagnosis(
            fix_type="intent_keyword", intent="REFUND", keywords=new_kws
        )
        result = fixer.apply_fix(diag)

        assert result.success is True
        assert "Added" in result.description
        assert rules_path in result.files_modified

        after = Path(rules_path).read_text(encoding="utf-8")
        assert after != before
        for kw in new_kws:
            assert kw in after

        # Rollback
        fixer.rollback()
        restored = Path(rules_path).read_text(encoding="utf-8")
        assert restored == before

    def test_duplicate_keywords_not_added(self) -> None:
        """Keywords already present should not be re-added."""
        import importlib
        from pathlib import Path

        fixer = Fixer(dry_run=False)
        rules_mod = importlib.import_module("ticketpilot.classification.rules")
        assert rules_mod.__file__ is not None
        rules_path = str(Path(rules_mod.__file__).resolve())
        fixer._backup_file(rules_path)

        before = Path(rules_path).read_text(encoding="utf-8")

        diag = _make_diagnosis(
            fix_type="intent_keyword",
            intent="REFUND",
            keywords=["退款"],  # "退款" is already in REFUND keywords
        )
        result = fixer.apply_fix(diag)
        assert result.success is True
        assert "already present" in result.description

        after = Path(rules_path).read_text(encoding="utf-8")
        assert after == before  # no change

        fixer.rollback()

    def test_missing_intent_returns_error(self) -> None:
        """Non-existent intent should fail in non-dry-run mode."""
        fixer = Fixer(dry_run=False)
        import importlib
        from pathlib import Path

        rules_mod = importlib.import_module("ticketpilot.classification.rules")
        assert rules_mod.__file__ is not None
        rules_path = str(Path(rules_mod.__file__).resolve())
        fixer._backup_file(rules_path)

        diag = _make_diagnosis(fix_type="intent_keyword", intent="NONEXISTENT")
        result = fixer.apply_fix(diag)
        assert result.success is False
        assert "not found" in (result.error or "")


# ---------------------------------------------------------------------------
# Fixer: risk keyword fix (real write + rollback)
# ---------------------------------------------------------------------------


class TestFixerRiskKeywords:
    def test_add_keywords_real_write(self) -> None:
        from pathlib import Path
        import importlib

        fixer = Fixer(dry_run=False)
        risk_mod = importlib.import_module("ticketpilot.risk.rules")
        assert risk_mod.__file__ is not None
        risk_path = str(Path(risk_mod.__file__).resolve())
        fixer._backup_file(risk_path)

        before = Path(risk_path).read_text(encoding="utf-8")

        new_kws = ["举报侵权", "虚假宣传"]
        for kw in new_kws:
            assert kw not in before

        diag = _make_diagnosis(
            fix_type="risk_keyword",
            risk_flag="COMPLAINT_RISK",
            keywords=new_kws,
        )
        result = fixer.apply_fix(diag)
        assert result.success is True
        assert risk_path in result.files_modified

        after = Path(risk_path).read_text(encoding="utf-8")
        for kw in new_kws:
            assert kw in after

        fixer.rollback()
        restored = Path(risk_path).read_text(encoding="utf-8")
        assert restored == before


# ---------------------------------------------------------------------------
# Fixer: confidence threshold fix (real write + rollback)
# ---------------------------------------------------------------------------


class TestFixerConfidenceThreshold:
    def test_change_threshold_real_write(self) -> None:
        from pathlib import Path
        import importlib

        fixer = Fixer(dry_run=False)
        config_mod = importlib.import_module("ticketpilot.config")
        assert config_mod.__file__ is not None
        config_path = str(Path(config_mod.__file__).resolve())
        fixer._backup_file(config_path)

        before = Path(config_path).read_text(encoding="utf-8")

        diag = _make_diagnosis(
            fix_type="confidence_threshold",
            threshold_name="CONFIDENCE_MEDIUM",
            new_value=0.55,
        )
        result = fixer.apply_fix(diag)
        assert result.success is True
        assert "0.55" in result.description

        after = Path(config_path).read_text(encoding="utf-8")
        assert "CONFIDENCE_MEDIUM = 0.55" in after

        fixer.rollback()
        restored = Path(config_path).read_text(encoding="utf-8")
        assert restored == before

    def test_missing_threshold_name(self) -> None:
        fixer = Fixer(dry_run=True)
        diag = _make_diagnosis(
            fix_type="confidence_threshold",
            threshold_name=None,
            new_value=0.55,
        )
        result = fixer.apply_fix(diag)
        assert result.success is False
        assert "Missing" in result.description


# ---------------------------------------------------------------------------
# Fixer: rollback
# ---------------------------------------------------------------------------


class TestFixerRollback:
    def test_rollback_restores_all_files(self) -> None:
        import importlib
        from pathlib import Path

        fixer = Fixer(dry_run=False)
        rules_mod = importlib.import_module("ticketpilot.classification.rules")
        risk_mod = importlib.import_module("ticketpilot.risk.rules")
        assert rules_mod.__file__ is not None
        assert risk_mod.__file__ is not None
        rules_path = str(Path(rules_mod.__file__).resolve())
        risk_path = str(Path(risk_mod.__file__).resolve())

        fixer._backup_file(rules_path)
        fixer._backup_file(risk_path)

        rules_before = Path(rules_path).read_text(encoding="utf-8")
        risk_before = Path(risk_path).read_text(encoding="utf-8")

        # Apply a keyword fix
        diag = _make_diagnosis(
            fix_type="intent_keyword", intent="REFUND", keywords=["测试回滚"]
        )
        fixer.apply_fix(diag)
        assert Path(rules_path).read_text(encoding="utf-8") != rules_before

        # Rollback
        fixer.rollback()
        assert Path(rules_path).read_text(encoding="utf-8") == rules_before
        assert Path(risk_path).read_text(encoding="utf-8") == risk_before
