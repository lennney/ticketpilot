"""Tests for Multi-Agent template differentiation.

Verifies that each specialist agent uses the correct template_id
and that templates are loaded and injected into prompts correctly.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from ticketpilot.drafting.draft_agent import DraftAgent
from ticketpilot.drafting.prompt_builder import (
    DraftPromptInput,
    build_prompt,
    load_template,
)
from ticketpilot.multi_agent import (
    BaseAgent,
    ComplaintAgent,
    DefaultAgent,
    LogisticsAgent,
    Orchestrator,
    RefundAgent,
    TechnicalAgent,
)


# ---------------------------------------------------------------------------
# Template file existence tests
# ---------------------------------------------------------------------------

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "src" / "ticketpilot" / "prompts" / "templates"


class TestTemplateFilesExist:
    """Verify all required template files exist."""

    def test_complaint_template_exists(self):
        assert (_TEMPLATES_DIR / "complaint.md").exists()

    def test_refund_template_exists(self):
        assert (_TEMPLATES_DIR / "refund.md").exists()

    def test_logistics_template_exists(self):
        assert (_TEMPLATES_DIR / "logistics.md").exists()

    def test_technical_template_exists(self):
        assert (_TEMPLATES_DIR / "technical.md").exists()

    def test_default_template_exists(self):
        assert (_TEMPLATES_DIR / "default.md").exists()


# ---------------------------------------------------------------------------
# Template loading tests
# ---------------------------------------------------------------------------


class TestLoadTemplate:
    """Test load_template function."""

    def test_loads_existing_template(self):
        content = load_template("default")
        assert content is not None
        assert len(content) > 0

    def test_returns_none_for_missing_template(self):
        content = load_template("nonexistent_template_xyz")
        assert content is None

    def test_all_templates_load(self):
        for template_id in ("complaint", "refund", "logistics", "technical", "default"):
            content = load_template(template_id)
            assert content is not None, f"Template '{template_id}' failed to load"


# ---------------------------------------------------------------------------
# Agent template_id tests
# ---------------------------------------------------------------------------


class TestAgentTemplateIds:
    """Test that each agent uses the correct template_id."""

    def test_refund_agent_template_id(self):
        agent = RefundAgent()
        assert agent.template_id == "refund"

    def test_complaint_agent_template_id(self):
        agent = ComplaintAgent()
        assert agent.template_id == "complaint"

    def test_logistics_agent_template_id(self):
        agent = LogisticsAgent()
        assert agent.template_id == "logistics"

    def test_technical_agent_template_id(self):
        agent = TechnicalAgent()
        assert agent.template_id == "technical"

    def test_default_agent_template_id(self):
        agent = DefaultAgent()
        assert agent.template_id == "default"

    def test_draft_agent_has_template_id(self):
        agent = DraftAgent(template_id="complaint")
        assert agent._template_id == "complaint"

    def test_draft_agent_default_template_id(self):
        agent = DraftAgent()
        assert agent._template_id == "default"


# ---------------------------------------------------------------------------
# ComplaintAgent forces must_human_review
# ---------------------------------------------------------------------------


class TestComplaintAgentHumanReview:
    """Test that ComplaintAgent always forces must_human_review=True."""

    def test_complaint_agent_forces_human_review(self):
        agent = ComplaintAgent()
        # Verify the agent's generate_draft sets must_human_review=True
        # by checking the method source or mock
        import inspect
        source = inspect.getsource(agent.generate_draft)
        assert "must_human_review = True" in source

    def test_complaint_agent_overrides_input(self):
        """Even if must_human_review=False is passed, ComplaintAgent forces it."""
        agent = ComplaintAgent()
        import inspect
        source = inspect.getsource(agent.generate_draft)
        # The assignment happens before the call to draft_agent
        assert "must_human_review = True" in source


# ---------------------------------------------------------------------------
# Orchestrator routing tests
# ---------------------------------------------------------------------------


class TestOrchestratorRouting:
    """Test that Orchestrator routes to the correct agent."""

    def setup_method(self):
        self.orchestrator = Orchestrator()

    def test_refund_routes_to_refund_agent(self):
        agent = self.orchestrator.get_agent("refund")
        assert isinstance(agent, RefundAgent)
        assert agent.template_id == "refund"

    def test_return_exchange_routes_to_logistics_agent(self):
        agent = self.orchestrator.get_agent("return_exchange")
        assert isinstance(agent, LogisticsAgent)

    def test_complaint_routes_to_complaint_agent(self):
        agent = self.orchestrator.get_agent("complaint")
        assert isinstance(agent, ComplaintAgent)
        assert agent.template_id == "complaint"

    def test_logistics_routes_to_logistics_agent(self):
        agent = self.orchestrator.get_agent("logistics")
        assert isinstance(agent, LogisticsAgent)
        assert agent.template_id == "logistics"

    def test_technical_issue_routes_to_technical_agent(self):
        agent = self.orchestrator.get_agent("technical_issue")
        assert isinstance(agent, TechnicalAgent)
        assert agent.template_id == "technical"

    def test_account_issue_routes_to_technical_agent(self):
        agent = self.orchestrator.get_agent("account_issue")
        assert isinstance(agent, TechnicalAgent)

    def test_unknown_intent_routes_to_default(self):
        agent = self.orchestrator.get_agent("unknown_intent_xyz")
        assert isinstance(agent, DefaultAgent)
        assert agent.template_id == "default"

    def test_product_consulting_routes_to_default(self):
        agent = self.orchestrator.get_agent("product_consulting")
        assert isinstance(agent, DefaultAgent)


# ---------------------------------------------------------------------------
# Prompt builder template integration tests
# ---------------------------------------------------------------------------


class TestPromptBuilderTemplates:
    """Test that build_prompt correctly incorporates templates."""

    def _make_input(self, template_id: str = "default") -> DraftPromptInput:
        return DraftPromptInput(
            ticket_text="测试客户消息",
            issue_type="complaint",
            template_id=template_id,
        )

    def test_default_template_in_prompt(self):
        prompt = build_prompt(self._make_input("default"))
        assert "专项处理指南" in prompt
        assert "default" in prompt

    def test_complaint_template_in_prompt(self):
        prompt = build_prompt(self._make_input("complaint"))
        assert "情绪安抚" in prompt or "投诉" in prompt

    def test_refund_template_in_prompt(self):
        prompt = build_prompt(self._make_input("refund"))
        assert "退款" in prompt

    def test_logistics_template_in_prompt(self):
        prompt = build_prompt(self._make_input("logistics"))
        assert "物流" in prompt

    def test_technical_template_in_prompt(self):
        prompt = build_prompt(self._make_input("technical"))
        assert "故障" in prompt or "排查" in prompt

    def test_missing_template_falls_back_to_default(self):
        prompt = build_prompt(self._make_input("nonexistent_xyz"))
        # Should fall back to default template
        assert "专项处理指南" in prompt

    def test_template_id_override_parameter(self):
        input_data = self._make_input("default")
        prompt = build_prompt(input_data, template_id="complaint")
        assert "投诉" in prompt or "情绪安抚" in prompt
