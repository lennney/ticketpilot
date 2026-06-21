"""Runtime skill loader — loads business skills from skills/runtime/.

Each skill is a subdirectory containing:
  - SKILL.md        human-readable business recipe (documentation only)
  - planner_template.yaml   structured plan data (machine-readable)

Skill selection is deterministic: by skill_id, issue_type, or goal match.
Missing skills return a safe fallback, never crash.
Malformed files fail loudly with a clear error.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class SkillDefinition:
    """Immutable definition of a loaded business skill."""

    skill_id: str
    issue_type: str
    goal: str
    description: str
    match_keywords: list[str] = field(default_factory=list)
    required_tools: list[str] = field(default_factory=list)
    steps: list[dict[str, str]] = field(default_factory=list)

    def matches_text(self, text: str) -> bool:
        """Return True if any match_keyword appears in *text* (case-insensitive)."""
        if not self.match_keywords:
            return False
        lowered = text.lower()
        return any(kw.lower() in lowered for kw in self.match_keywords)


_SKILLS_BASE = Path("skills") / "runtime"

_FALLBACK_SKILL = SkillDefinition(
    skill_id="generic_support",
    issue_type="general",
    goal="Provide general support for the ticket",
    description="Fallback skill when no specific business skill matches",
    required_tools=[
        "normalize_ticket",
        "classify_ticket",
        "assess_risk",
        "retrieve_evidence",
        "generate_draft",
    ],
    steps=[
        {"step_id": "s1_normalize", "tool_name": "normalize_ticket"},
        {"step_id": "s2_classify", "tool_name": "classify_ticket"},
        {"step_id": "s3_assess_risk", "tool_name": "assess_risk"},
        {"step_id": "s4_retrieve_evidence", "tool_name": "retrieve_evidence"},
        {"step_id": "s5_generate_draft", "tool_name": "generate_draft"},
    ],
)

_KNOWN_TOOLS = frozenset(
    {
        "normalize_ticket",
        "classify_ticket",
        "assess_risk",
        "retrieve_evidence",
        "generate_draft",
    }
)


class SkillLoadError(Exception):
    """Raised when a skill file cannot be parsed or is malformed."""


def _validate_required_tools(tools: list[str]) -> None:
    """Validate that all required_tools are known tool names."""
    unknown = [t for t in tools if t not in _KNOWN_TOOLS]
    if unknown:
        raise SkillLoadError(f"unknown required_tools: {unknown}")


def _parse_skill_dir(skill_dir: Path) -> SkillDefinition:
    """Parse a single skill directory and return a SkillDefinition.

    The directory must contain a planner_template.yaml file.
    SKILL.md is read for documentation purposes; structured data comes from YAML.
    """
    yaml_path = skill_dir / "planner_template.yaml"
    md_path = skill_dir / "SKILL.md"

    if not yaml_path.exists():
        raise SkillLoadError(f"missing planner_template.yaml in {skill_dir}")
    if not md_path.exists():
        raise SkillLoadError(f"missing SKILL.md in {skill_dir}")

    with open(yaml_path, encoding="utf-8") as f:
        try:
            data: dict[str, Any] = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise SkillLoadError(f"invalid YAML in {yaml_path}: {e}") from e

    if not isinstance(data, dict):
        raise SkillLoadError(
            f"planner_template.yaml in {skill_dir} must contain a mapping"
        )

    skill_id = data.get("skill_id")
    if not skill_id or not isinstance(skill_id, str) or not skill_id.strip():
        raise SkillLoadError(
            f"planner_template.yaml in {skill_dir} missing valid 'skill_id'"
        )

    issue_type = data.get("issue_type", skill_id)
    goal = data.get("goal", "")
    description = data.get("description", "")
    match_keywords = data.get("match_keywords", [])
    required_tools = data.get("required_tools", [])
    steps = data.get("steps", [])

    if not isinstance(match_keywords, list):
        raise SkillLoadError(f"'match_keywords' must be a list in {yaml_path}")
    if not isinstance(required_tools, list):
        raise SkillLoadError(f"'required_tools' must be a list in {yaml_path}")

    _validate_required_tools(required_tools)

    return SkillDefinition(
        skill_id=skill_id.strip(),
        issue_type=issue_type.strip(),
        goal=goal,
        description=description,
        match_keywords=match_keywords,
        required_tools=required_tools,
        steps=steps,
    )


class SkillLoader:
    """Loads and selects business skills from skills/runtime/.

    Usage:
        loader = SkillLoader()
        loader.load_all()
        skill = loader.select_by_id("refund_request")
        skill = loader.select_by_text("我要退款")
    """

    def __init__(self, base_path: Path | str | None = None) -> None:
        self._base = Path(base_path) if base_path else _SKILLS_BASE
        self._skills: dict[str, SkillDefinition] = {}

    def load_all(self) -> list[SkillDefinition]:
        """Scan skills/runtime/ and load all valid skills.

        Returns the list of loaded skills.
        Skips non-directory entries and __pycache__.
        Raises SkillLoadError on malformed files.
        """
        if not self._base.exists():
            raise SkillLoadError(f"skills base directory not found: {self._base}")

        loaded: list[SkillDefinition] = []
        for entry in sorted(self._base.iterdir()):
            if not entry.is_dir():
                continue
            if entry.name.startswith("_"):
                continue
            skill = _parse_skill_dir(entry)
            if skill.skill_id in self._skills:
                raise SkillLoadError(
                    f"duplicate skill_id '{skill.skill_id}' in {entry}"
                )
            self._skills[skill.skill_id] = skill
            loaded.append(skill)

        return loaded

    def select_by_id(self, skill_id: str) -> SkillDefinition:
        """Look up a skill by its skill_id. Returns fallback if not found."""
        return self._skills.get(skill_id, _FALLBACK_SKILL)

    def select_by_issue_type(self, issue_type: str) -> SkillDefinition | None:
        """Find the first skill matching *issue_type*, or None."""
        for skill in self._skills.values():
            if skill.issue_type == issue_type:
                return skill
        return None

    def select_by_text(self, text: str) -> SkillDefinition:
        """Select the best skill by keyword matching against *text*.

        Priority order preserves the planner's complaint-first rule.
        Falls back to generic_support if no keywords match.
        """
        if not text or not text.strip():
            return _FALLBACK_SKILL

        # Check complaint first (highest priority)
        complaint = self._skills.get("complaint_escalation")
        if complaint and complaint.matches_text(text):
            return complaint

        for skill in self._skills.values():
            if skill.skill_id == "complaint_escalation":
                continue  # already checked
            if skill.matches_text(text):
                return skill

        return _FALLBACK_SKILL

    def list_skills(self) -> list[SkillDefinition]:
        """Return all loaded skills."""
        return list(self._skills.values())

    @property
    def fallback(self) -> SkillDefinition:
        return _FALLBACK_SKILL
