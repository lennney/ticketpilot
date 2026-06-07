"""Tests for the self-reflection skills system."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from ticketpilot.skills.schema import SkillLibrary, SkillPattern
from ticketpilot.skills.loader import (
    load_skill_library,
    select_relevant_skills,
    save_skill_library,
)
from ticketpilot.skills.reflector import reflect_on_draft, ReflectionResult
from ticketpilot.skills.generator import generate_skill_from_success


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


class TestSkillPattern:
    """Tests for SkillPattern model."""

    def test_create_minimal(self):
        pattern = SkillPattern(
            skill_id="test_1", intent="refund", name="Test", description="desc"
        )
        assert pattern.skill_id == "test_1"
        assert pattern.intent == "refund"
        assert pattern.keywords == []
        assert pattern.success_count == 0
        assert pattern.tone == "professional"

    def test_create_full(self):
        pattern = SkillPattern(
            skill_id="legal_v1",
            intent="complaint",
            name="Legal threat",
            description="Handle legal threats",
            keywords=["律师", "起诉"],
            resolution_steps=["声明免责", "转法务"],
            risk_flags_to_acknowledge=["legal_risk"],
            tone="professional",
            success_count=5,
        )
        assert len(pattern.keywords) == 2
        assert len(pattern.resolution_steps) == 2
        assert "legal_risk" in pattern.risk_flags_to_acknowledge

    def test_skill_id_required(self):
        with pytest.raises(Exception):
            SkillPattern(intent="refund", name="Bad", description="desc")


class TestSkillLibrary:
    """Tests for SkillLibrary model."""

    def test_empty_library(self):
        lib = SkillLibrary()
        assert lib.version == "1.0"
        assert len(lib.skills) == 0

    def test_library_with_skills(self):
        skill = SkillPattern(
            skill_id="s1", intent="refund", name="S1", description="desc"
        )
        lib = SkillLibrary(skills={"s1": skill})
        assert len(lib.skills) == 1
        assert lib.skills["s1"].name == "S1"


# ---------------------------------------------------------------------------
# Loader tests
# ---------------------------------------------------------------------------


class TestLoader:
    """Tests for load_skill_library and select_relevant_skills."""

    def test_load_default_library(self):
        lib = load_skill_library()
        assert len(lib.skills) >= 5
        assert "refund_v1" in lib.skills
        assert "complaint_v1" in lib.skills
        assert "legal_v1" in lib.skills
        assert "logistics_v1" in lib.skills
        assert "technical_v1" in lib.skills

    def test_load_nonexistent_file(self):
        lib = load_skill_library("/tmp/nonexistent_skills.json")
        assert len(lib.skills) == 0

    def test_select_by_intent(self):
        lib = load_skill_library()
        skills = select_relevant_skills(lib, "complaint", [])
        assert len(skills) > 0
        # complaint_v1 and legal_v1 both have intent=complaint
        intents = {s.intent for s in skills}
        assert "complaint" in intents

    def test_select_by_risk_flags(self):
        lib = load_skill_library()
        skills = select_relevant_skills(lib, "complaint", ["legal_risk"])
        # legal_v1 should rank highest (intent match + risk flag match)
        assert skills[0].skill_id == "legal_v1"

    def test_select_no_match(self):
        lib = load_skill_library()
        skills = select_relevant_skills(lib, "nonexistent_intent", [])
        assert len(skills) == 0

    def test_select_top_k(self):
        lib = load_skill_library()
        skills = select_relevant_skills(lib, "complaint", [], top_k=1)
        assert len(skills) == 1


# ---------------------------------------------------------------------------
# Reflector tests
# ---------------------------------------------------------------------------


class TestReflector:
    """Tests for reflect_on_draft."""

    def test_pass_when_no_issues(self):
        skill = SkillPattern(
            skill_id="test",
            intent="refund",
            name="Test",
            description="desc",
            resolution_steps=["确认订单号"],
        )
        result = reflect_on_draft("已确认您的订单号123456", skill, [])
        assert result.passed is True
        assert len(result.issues) == 0

    def test_fail_legal_risk_missing_declaration(self):
        skill = SkillPattern(
            skill_id="legal_v1",
            intent="complaint",
            name="Legal",
            description="desc",
            risk_flags_to_acknowledge=["legal_risk"],
        )
        result = reflect_on_draft("我们会尽快处理您的问题", skill, ["legal_risk"])
        assert result.passed is False
        assert any("法律" in issue for issue in result.issues)

    def test_pass_legal_risk_with_declaration(self):
        skill = SkillPattern(
            skill_id="legal_v1",
            intent="complaint",
            name="Legal",
            description="desc",
            risk_flags_to_acknowledge=["legal_risk"],
        )
        result = reflect_on_draft(
            "我们已收到您的律师函，建议咨询法律专业人士", skill, ["legal_risk"]
        )
        assert result.passed is True

    def test_empathetic_tone_suggestion(self):
        skill = SkillPattern(
            skill_id="test",
            intent="complaint",
            name="Test",
            description="desc",
            tone="empathetic",
        )
        result = reflect_on_draft("我们会处理", skill, [])
        assert any("同理心" in s for s in result.suggestions)

    def test_empathetic_tone_pass(self):
        skill = SkillPattern(
            skill_id="test",
            intent="complaint",
            name="Test",
            description="desc",
            tone="empathetic",
        )
        result = reflect_on_draft("非常抱歉给您带来不便，我们理解您的感受", skill, [])
        # Should have no empathetic tone suggestion
        assert not any("同理心" in s for s in result.suggestions)


# ---------------------------------------------------------------------------
# Generator tests
# ---------------------------------------------------------------------------


class TestGenerator:
    """Tests for generate_skill_from_success."""

    def test_generate_basic(self):
        skill = generate_skill_from_success(
            intent="complaint",
            original_text="我要投诉你们态度差",
            approved_draft="非常抱歉给您带来不好的体验。我们会认真处理您的投诉。",
            risk_flags=["complaint_risk"],
        )
        assert skill.intent == "complaint"
        assert skill.success_count == 1
        assert "投诉" in skill.keywords
        assert len(skill.resolution_steps) > 0

    def test_generate_with_legal_keywords(self):
        skill = generate_skill_from_success(
            intent="complaint",
            original_text="请你们律师联系我，准备起诉",
            approved_draft="我们已记录您的诉求。建议您咨询专业律师。",
            risk_flags=["legal_risk"],
        )
        assert "律师" in skill.keywords
        assert "legal_risk" in skill.risk_flags_to_acknowledge


# ---------------------------------------------------------------------------
# Persistence tests
# ---------------------------------------------------------------------------


class TestPersistence:
    """Tests for save_skill_library round-trip."""

    def test_save_and_reload(self):
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            tmp_path = f.name

        try:
            # Load default, save to temp, reload
            lib = load_skill_library()
            lib.skills["test_persist"] = SkillPattern(
                skill_id="test_persist",
                intent="test",
                name="Persist Test",
                description="Testing save/load round-trip",
                success_count=1,
            )
            save_skill_library(lib, path=tmp_path)

            reloaded = load_skill_library(tmp_path)
            assert "test_persist" in reloaded.skills
            assert reloaded.skills["test_persist"].name == "Persist Test"
            assert len(reloaded.skills) == len(lib.skills)
        finally:
            Path(tmp_path).unlink(missing_ok=True)

    def test_save_creates_parent_dirs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "nested" / "dir" / "skills.json")
            lib = SkillLibrary(
                skills={
                    "s1": SkillPattern(
                        skill_id="s1", intent="test", name="S1", description="desc"
                    )
                }
            )
            save_skill_library(lib, path=path)
            assert Path(path).exists()
            reloaded = load_skill_library(path)
            assert "s1" in reloaded.skills

    def test_save_with_datetime_fields(self):
        with tempfile.NamedTemporaryFile(
            suffix=".json", delete=False, mode="w"
        ) as f:
            tmp_path = f.name

        try:
            lib = SkillLibrary()
            lib.skills["dt_test"] = SkillPattern(
                skill_id="dt_test",
                intent="test",
                name="DateTime Test",
                description="desc",
                last_used=datetime(2026, 6, 7, 12, 0, 0, tzinfo=timezone.utc),
                created_at=datetime(2026, 6, 1, 0, 0, 0, tzinfo=timezone.utc),
            )
            save_skill_library(lib, path=tmp_path)

            # Verify JSON is valid and datetimes are ISO format
            data = json.loads(Path(tmp_path).read_text(encoding="utf-8"))
            skill = data["skills"]["dt_test"]
            assert "2026-06-07" in skill["last_used"]
            assert "2026-06-01" in skill["created_at"]

            # Verify reload works
            reloaded = load_skill_library(tmp_path)
            assert reloaded.skills["dt_test"].last_used is not None
        finally:
            Path(tmp_path).unlink(missing_ok=True)
