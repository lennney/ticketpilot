"""Tests for PromptManager — Factor 2: Own Your Prompts."""

import pytest

from ticketpilot.prompts.manager import PromptManager, PromptVersion


class TestPromptManager:
    """Tests for PromptManager CRUD and rendering."""

    def _make_prompt(self, **overrides) -> PromptVersion:
        defaults = {
            "prompt_id": "draft_reply",
            "version": "1.0.0",
            "template": "你是一个客服助手。请回复：{ticket_text}",
            "variables": ["ticket_text"],
            "changelog": "Initial version",
        }
        defaults.update(overrides)
        return PromptVersion(**defaults)

    def test_register_and_get(self):
        """Can register and retrieve a prompt."""
        pm = PromptManager()
        pm.register(self._make_prompt())

        result = pm.get("draft_reply")
        assert result.version == "1.0.0"
        assert "{ticket_text}" in result.template

    def test_get_specific_version(self):
        """Can get a specific version."""
        pm = PromptManager()
        pm.register(self._make_prompt(version="1.0.0"))
        pm.register(self._make_prompt(version="2.0.0", template="新版：{ticket_text}"))

        v1 = pm.get("draft_reply", version="1.0.0")
        assert v1.version == "1.0.0"

        v2 = pm.get("draft_reply", version="2.0.0")
        assert v2.template == "新版：{ticket_text}"

    def test_get_latest(self):
        """"latest" returns the last registered version."""
        pm = PromptManager()
        pm.register(self._make_prompt(version="1.0.0"))
        pm.register(self._make_prompt(version="2.0.0"))

        latest = pm.get("draft_reply", version="latest")
        assert latest.version == "2.0.0"

    def test_get_nonexistent_raises(self):
        """KeyError for unknown prompt_id."""
        pm = PromptManager()
        with pytest.raises(KeyError, match="not found"):
            pm.get("nonexistent")

    def test_get_nonexistent_version_raises(self):
        """KeyError for unknown version."""
        pm = PromptManager()
        pm.register(self._make_prompt(version="1.0.0"))
        with pytest.raises(KeyError, match="Version"):
            pm.get("draft_reply", version="99.0.0")

    def test_render(self):
        """Can render a template with variables."""
        pm = PromptManager()
        pm.register(self._make_prompt())

        result = pm.render("draft_reply", {"ticket_text": "我要退款"})
        assert result == "你是一个客服助手。请回复：我要退款"

    def test_list_versions(self):
        """Can list all versions of a prompt."""
        pm = PromptManager()
        pm.register(self._make_prompt(version="1.0.0"))
        pm.register(self._make_prompt(version="1.1.0"))
        pm.register(self._make_prompt(version="2.0.0"))

        versions = pm.list_versions("draft_reply")
        assert len(versions) == 3
        assert [v.version for v in versions] == ["1.0.0", "1.1.0", "2.0.0"]

    def test_list_prompts(self):
        """Can list all prompt IDs."""
        pm = PromptManager()
        pm.register(self._make_prompt(prompt_id="draft_reply"))
        pm.register(self._make_prompt(prompt_id="risk_assessment"))

        prompts = pm.list_prompts()
        assert "draft_reply" in prompts
        assert "risk_assessment" in prompts

    def test_list_versions_empty(self):
        """Empty list for unknown prompt_id."""
        pm = PromptManager()
        assert pm.list_versions("nonexistent") == []
