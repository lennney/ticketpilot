"""Version-managed prompt templates for TicketPilot.

Factor 2: Own Your Prompts

Centralizes prompts with version tracking, enabling:
- A/B testing different prompt versions
- Rollback to previous versions
- Audit trail of prompt changes
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class PromptVersion(BaseModel):
    """A versioned prompt template."""

    prompt_id: str = Field(description="Unique prompt identifier")
    version: str = Field(description="Semver version (e.g., '1.0.0')")
    template: str = Field(
        description="Prompt template text (supports {variable} placeholders)"
    )
    variables: list[str] = Field(
        default_factory=list, description="Required template variables"
    )
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    changelog: str = Field(default="", description="What changed in this version")


class PromptManager:
    """Version-managed prompt template store.

    Usage:
        pm = PromptManager("prompts/")
        pm.register(PromptVersion(
            prompt_id="draft_reply",
            version="1.0.0",
            template="你是一个客服助手。请根据以下信息回复：{ticket_text}",
            variables=["ticket_text"],
        ))
        rendered = pm.render("draft_reply", {"ticket_text": "退款申请"})
    """

    def __init__(self, prompts_dir: str | Path | None = None) -> None:
        self._prompts: dict[str, list[PromptVersion]] = {}
        if prompts_dir:
            self._load_from_dir(Path(prompts_dir))

    def register(self, prompt: PromptVersion) -> None:
        """Register a new prompt version."""
        if prompt.prompt_id not in self._prompts:
            self._prompts[prompt.prompt_id] = []
        self._prompts[prompt.prompt_id].append(prompt)

    def get(self, prompt_id: str, version: str = "latest") -> PromptVersion:
        """Get a prompt by ID and version.

        Args:
            prompt_id: The prompt identifier.
            version: Specific version or "latest" (default).

        Returns:
            The matching PromptVersion.

        Raises:
            KeyError: If prompt_id not found or version not found.
        """
        if prompt_id not in self._prompts:
            raise KeyError(f"Prompt '{prompt_id}' not found")

        versions = self._prompts[prompt_id]
        if not versions:
            raise KeyError(f"Prompt '{prompt_id}' has no versions")

        if version == "latest":
            return versions[-1]

        for v in versions:
            if v.version == version:
                return v

        raise KeyError(f"Version '{version}' not found for prompt '{prompt_id}'")

    def render(
        self, prompt_id: str, variables: dict[str, Any], version: str = "latest"
    ) -> str:
        """Render a prompt template with variables.

        Args:
            prompt_id: The prompt identifier.
            variables: Template variable values.
            version: Specific version or "latest".

        Returns:
            Rendered prompt string.
        """
        pv = self.get(prompt_id, version)
        return pv.template.format(**variables)

    def list_versions(self, prompt_id: str) -> list[PromptVersion]:
        """List all versions of a prompt."""
        if prompt_id not in self._prompts:
            return []
        return list(self._prompts[prompt_id])

    def list_prompts(self) -> list[str]:
        """List all registered prompt IDs."""
        return list(self._prompts.keys())

    def _load_from_dir(self, prompts_dir: Path) -> None:
        """Load prompt templates from a directory."""
        if not prompts_dir.exists():
            return
        # Future: load from YAML/JSON files in the directory
