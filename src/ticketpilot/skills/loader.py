"""Load and select skills from the skill library."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from ticketpilot.skills.schema import SkillLibrary, SkillPattern

logger = logging.getLogger(__name__)

_DEFAULT_LIBRARY_PATH = "data/skills/library.json"


def load_skill_library(path: str = _DEFAULT_LIBRARY_PATH) -> SkillLibrary:
    """Load the skill library from a JSON file.

    Returns an empty library if the file does not exist.
    """
    p = Path(path)
    if not p.exists():
        logger.info("Skill library not found at %s, returning empty library", path)
        return SkillLibrary()
    data = json.loads(p.read_text(encoding="utf-8"))
    return SkillLibrary(**data)


def select_relevant_skills(
    library: SkillLibrary,
    intent: str,
    risk_flags: list[str],
    top_k: int = 3,
) -> list[SkillPattern]:
    """Select the most relevant skills for a given intent and risk profile.

    Scoring:
      - +10 for exact intent match
      - +5 per matching risk flag
      - +1 per prior success
    """
    candidates: list[tuple[int, SkillPattern]] = []
    for skill in library.skills.values():
        score = 0
        if skill.intent == intent:
            score += 10
        for flag in risk_flags:
            if flag in skill.risk_flags_to_acknowledge:
                score += 5
        if score > 0:
            score += skill.success_count
            candidates.append((score, skill))

    candidates.sort(key=lambda x: x[0], reverse=True)
    return [skill for _, skill in candidates[:top_k]]


def save_skill_library(
    library: SkillLibrary,
    path: str = _DEFAULT_LIBRARY_PATH,
) -> None:
    """Save the skill library to a JSON file."""
    import json
    from pathlib import Path

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = library.model_dump(mode="json")
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
