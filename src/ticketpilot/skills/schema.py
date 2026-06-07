"""Skill data structures for the self-reflection system."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class SkillPattern(BaseModel):
    """A single resolution pattern (skill) learned from past successes."""

    skill_id: str = Field(..., min_length=1)
    intent: str
    name: str
    description: str
    keywords: list[str] = Field(default_factory=list)
    resolution_steps: list[str] = Field(default_factory=list)
    risk_flags_to_acknowledge: list[str] = Field(default_factory=list)
    tone: str = "professional"
    success_count: int = 0
    last_used: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SkillLibrary(BaseModel):
    """Collection of skills, loadable from JSON."""

    version: str = "1.0"
    skills: dict[str, SkillPattern] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
