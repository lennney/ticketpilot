"""Unit tests for SkillLoader (Batch 4).

Tests use the real skills/runtime/ directory to validate loading.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from ticketpilot.agent.skill_loader import (
    SkillLoadError,
    SkillLoader,
)


# ---------------------------------------------------------------------------
# Real directory loading
# ---------------------------------------------------------------------------


class TestLoadAll:
    def test_loads_four_skills(self):
        loader = SkillLoader()
        skills = loader.load_all()
        assert len(skills) == 4

    def test_loaded_skill_ids(self):
        loader = SkillLoader()
        loader.load_all()
        ids = sorted(s.skill_id for s in loader.list_skills())
        assert ids == [
            "account_issue",
            "complaint_escalation",
            "refund_request",
            "technical_issue",
        ]

    def test_each_skill_has_required_fields(self):
        loader = SkillLoader()
        loader.load_all()
        for skill in loader.list_skills():
            assert skill.skill_id
            assert skill.issue_type
            assert skill.goal
            assert skill.description
            assert isinstance(skill.match_keywords, list)
            assert len(skill.required_tools) > 0
            assert len(skill.steps) > 0


# ---------------------------------------------------------------------------
# Selection
# ---------------------------------------------------------------------------


class TestSelection:
    def test_select_by_id_refund(self):
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_id("refund_request")
        assert skill.skill_id == "refund_request"

    def test_select_by_id_complaint(self):
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_id("complaint_escalation")
        assert skill.skill_id == "complaint_escalation"

    def test_select_by_id_account(self):
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_id("account_issue")
        assert skill.skill_id == "account_issue"

    def test_select_by_id_technical(self):
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_id("technical_issue")
        assert skill.skill_id == "technical_issue"

    def test_unknown_id_falls_back(self):
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_id("nonexistent")
        assert skill.skill_id == "generic_support"

    def test_select_by_issue_type_refund(self):
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_issue_type("refund")
        assert skill is not None
        assert skill.skill_id == "refund_request"

    def test_select_by_issue_type_unknown(self):
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_issue_type("bogus")
        assert skill is None

    def test_select_by_text_refund_keyword(self):
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_text("我要退款")
        assert skill.skill_id == "refund_request"

    def test_select_by_text_complaint(self):
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_text("投诉商家")
        assert skill.skill_id == "complaint_escalation"

    def test_complaint_priority_over_refund(self):
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_text("投诉退款")
        assert skill.skill_id == "complaint_escalation"

    def test_select_by_text_account(self):
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_text("账号被盗")
        assert skill.skill_id == "account_issue"

    def test_select_by_text_technical(self):
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_text("系统故障")
        assert skill.skill_id == "technical_issue"

    def test_select_by_text_fallback(self):
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_text("你好")
        assert skill.skill_id == "generic_support"

    def test_select_by_text_empty(self):
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_text("")
        assert skill.skill_id == "generic_support"


# ---------------------------------------------------------------------------
# Fallback skill properties
# ---------------------------------------------------------------------------


class TestFallback:
    def test_fallback_has_core_tools(self):
        assert "normalize_ticket" in self.SKILLS_BASE.fallback.required_tools
        assert "generate_draft" in self.SKILLS_BASE.fallback.required_tools

    def test_fallback_has_five_steps(self):
        assert len(self.SKILLS_BASE.fallback.steps) == 5

    @property
    def SKILLS_BASE(self):
        from ticketpilot.agent.skill_loader import _FALLBACK_SKILL

        return type("_", (), {"fallback": _FALLBACK_SKILL})()


# ---------------------------------------------------------------------------
# Malformed / missing directories
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_missing_directory_raises(self):
        loader = SkillLoader(base_path=Path("/tmp/nonexistent_skills_xyz"))
        with pytest.raises(SkillLoadError, match="not found"):
            loader.load_all()

    def test_missing_planner_template(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "test_skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("# Test")
            loader = SkillLoader(base_path=Path(tmp))
            with pytest.raises(SkillLoadError, match="missing planner_template.yaml"):
                loader.load_all()

    def test_missing_skill_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "test_skill"
            skill_dir.mkdir()
            with open(skill_dir / "planner_template.yaml", "w") as f:
                yaml.dump(
                    {"skill_id": "test", "required_tools": ["normalize_ticket"]}, f
                )
            loader = SkillLoader(base_path=Path(tmp))
            with pytest.raises(SkillLoadError, match="missing SKILL.md"):
                loader.load_all()

    def test_invalid_yaml_content(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "bad_skill"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("# Bad")
            (skill_dir / "planner_template.yaml").write_text(": broken yaml [")
            loader = SkillLoader(base_path=Path(tmp))
            with pytest.raises(SkillLoadError):
                loader.load_all()

    def test_unknown_tool_in_required_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill_dir = Path(tmp) / "bad_tools"
            skill_dir.mkdir()
            (skill_dir / "SKILL.md").write_text("# Bad")
            with open(skill_dir / "planner_template.yaml", "w") as f:
                yaml.dump(
                    {
                        "skill_id": "bad",
                        "required_tools": ["nonexistent_tool"],
                    },
                    f,
                )
            loader = SkillLoader(base_path=Path(tmp))
            with pytest.raises(SkillLoadError, match="unknown required_tools"):
                loader.load_all()

    def test_duplicate_skill_id_detected(self):
        with tempfile.TemporaryDirectory() as tmp:
            for name in ("dup_a", "dup_b"):
                d = Path(tmp) / name
                d.mkdir()
                (d / "SKILL.md").write_text(f"# {name}")
                with open(d / "planner_template.yaml", "w") as f:
                    yaml.dump(
                        {
                            "skill_id": "duplicate",
                            "required_tools": ["normalize_ticket"],
                        },
                        f,
                    )
            loader = SkillLoader(base_path=Path(tmp))
            with pytest.raises(SkillLoadError, match="duplicate skill_id"):
                loader.load_all()


# ---------------------------------------------------------------------------
# Match keywords
# ---------------------------------------------------------------------------


class TestMatchKeywords:
    def test_refund_keywords_match(self):
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_id("refund_request")
        assert skill.matches_text("我要退款") is True
        assert skill.matches_text("hello world") is False

    def test_chinese_and_english_keywords(self):
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_id("refund_request")
        assert skill.matches_text("I want a refund") is True
