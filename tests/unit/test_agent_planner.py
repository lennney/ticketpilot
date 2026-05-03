"""Unit tests for DeterministicTaskPlanner (Batch 3)."""

import pytest

from ticketpilot.agent.planner import DeterministicTaskPlanner
from ticketpilot.agent.schemas import AgentPlan


@pytest.fixture
def planner() -> DeterministicTaskPlanner:
    return DeterministicTaskPlanner()


# ---------------------------------------------------------------------------
# Template selection — Chinese keywords
# ---------------------------------------------------------------------------

class TestTemplateSelectionChinese:
    def test_refund_keywords(self, planner):
        assert planner.select_template("我要退款") == "refund_request"
        assert planner.select_template("申请退钱") == "refund_request"
        assert planner.select_template("退费问题") == "refund_request"

    def test_return_exchange_keywords(self, planner):
        assert planner.select_template("我要换货") == "return_exchange"
        assert planner.select_template("退货申请") == "return_exchange"
        assert planner.select_template("退换处理") == "return_exchange"

    def test_complaint_keywords(self, planner):
        assert planner.select_template("投诉客服") == "complaint_escalation"
        assert planner.select_template("我要举报") == "complaint_escalation"
        assert planner.select_template("法律纠纷") == "complaint_escalation"
        assert planner.select_template("起诉商家") == "complaint_escalation"
        assert planner.select_template("要求赔偿") == "complaint_escalation"

    def test_complaint_priority_over_refund(self, planner):
        """Complaint escalation must win over refund when both match."""
        assert planner.select_template("要求赔偿退款") == "complaint_escalation"
        assert planner.select_template("投诉退货") == "complaint_escalation"

    def test_complaint_priority_over_logistics(self, planner):
        assert planner.select_template("投诉物流") == "complaint_escalation"

    def test_account_issue(self, planner):
        assert planner.select_template("账号被盗") == "account_issue"
        assert planner.select_template("登录不了") == "account_issue"
        assert planner.select_template("忘记密码") == "account_issue"
        assert planner.select_template("账户安全") == "account_issue"

    def test_logistics_query(self, planner):
        assert planner.select_template("物流太慢") == "logistics_query"
        assert planner.select_template("快递没到") == "logistics_query"
        assert planner.select_template("没收到货") == "logistics_query"
        assert planner.select_template("配送问题") == "logistics_query"

    def test_technical_issue(self, planner):
        assert planner.select_template("系统故障") == "technical_issue"
        assert planner.select_template("页面报错") == "technical_issue"
        assert planner.select_template("功能不能用") == "technical_issue"
        assert planner.select_template("程序崩溃") == "technical_issue"


# ---------------------------------------------------------------------------
# Template selection — English keywords
# ---------------------------------------------------------------------------

class TestTemplateSelectionEnglish:
    def test_refund_english(self, planner):
        assert planner.select_template("I want a refund") == "refund_request"

    def test_return_exchange_english(self, planner):
        assert planner.select_template("I want to return this") == "return_exchange"
        assert planner.select_template("exchange item") == "return_exchange"

    def test_complaint_english(self, planner):
        assert planner.select_template("file a complaint") == "complaint_escalation"
        assert planner.select_template("compensation") == "complaint_escalation"

    def test_account_english(self, planner):
        assert planner.select_template("login failed") == "account_issue"
        assert planner.select_template("account issue") == "account_issue"

    def test_logistics_english(self, planner):
        assert planner.select_template("delivery delay") == "logistics_query"
        assert planner.select_template("shipping address") == "logistics_query"

    def test_technical_english(self, planner):
        assert planner.select_template("bug found") == "technical_issue"
        assert planner.select_template("error message") == "technical_issue"


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------

class TestFallback:
    def test_generic_fallback(self, planner):
        assert planner.select_template("你好，请问一下") == "generic_support"

    def test_empty_text_fallback(self, planner):
        assert planner.select_template("") == "generic_support"

    def test_whitespace_text_fallback(self, planner):
        assert planner.select_template("   ") == "generic_support"

    def test_unknown_text_generic(self, planner):
        assert planner.select_template("hello world foo bar baz") == "generic_support"


# ---------------------------------------------------------------------------
# create_plan
# ---------------------------------------------------------------------------

class TestCreatePlan:
    def test_returns_agent_plan(self, planner):
        plan = planner.create_plan("我要退款")
        assert isinstance(plan, AgentPlan)

    def test_plan_has_five_steps(self, planner):
        plan = planner.create_plan("我要退款")
        assert len(plan.steps) == 5

    def test_step_ids_are_deterministic(self, planner):
        plan = planner.create_plan("我要退款")
        step_ids = [s.step_id for s in plan.steps]
        assert step_ids == [
            "s1_normalize",
            "s2_classify",
            "s3_assess_risk",
            "s4_retrieve_evidence",
            "s5_generate_draft",
        ]

    def test_required_tools_are_core_five(self, planner):
        plan = planner.create_plan("投诉")
        assert sorted(plan.required_tools) == sorted([
            "normalize_ticket",
            "classify_ticket",
            "assess_risk",
            "retrieve_evidence",
            "generate_draft",
        ])

    def test_constraints_include_no_auto_send(self, planner):
        plan = planner.create_plan("我要退款")
        assert any("No auto-send" in c for c in plan.constraints)

    def test_constraints_include_evidence_grounded(self, planner):
        plan = planner.create_plan("我要退款")
        assert any("evidence" in c.lower() for c in plan.constraints)

    def test_constraints_include_human_review(self, planner):
        plan = planner.create_plan("我要退款")
        assert any("human review" in c.lower() for c in plan.constraints)

    def test_complaint_has_escalation_constraint(self, planner):
        plan = planner.create_plan("投诉")
        assert any("Escalate" in c for c in plan.constraints)

    def test_same_input_gives_equivalent_plan(self, planner):
        plan_a = planner.create_plan("我要退款")
        plan_b = planner.create_plan("我要退款")
        assert plan_a.goal == plan_b.goal
        assert [s.step_id for s in plan_a.steps] == [s.step_id for s in plan_b.steps]

    def test_empty_text_raises_value_error(self, planner):
        with pytest.raises(ValueError, match="ticket text must not be empty"):
            planner.create_plan("")

    def test_whitespace_text_raises(self, planner):
        with pytest.raises(ValueError, match="ticket text must not be empty"):
            planner.create_plan("   ")

    def test_success_criteria_non_empty(self, planner):
        plan = planner.create_plan("我要退款")
        assert len(plan.success_criteria) > 0

    def test_no_duplicate_step_ids(self, planner):
        plan = planner.create_plan("我要退款")
        ids = [s.step_id for s in plan.steps]
        assert len(ids) == len(set(ids))

    def test_each_step_has_correct_tool_name(self, planner):
        plan = planner.create_plan("我要退款")
        tool_names = [s.tool_name for s in plan.steps]
        assert tool_names == [
            "normalize_ticket",
            "classify_ticket",
            "assess_risk",
            "retrieve_evidence",
            "generate_draft",
        ]

    def test_goal_reflects_template(self, planner):
        plan = planner.create_plan("我要退款")
        assert "refund" in plan.goal.lower()
        plan2 = planner.create_plan("投诉")
        assert "complaint" in plan2.goal.lower() or "escalation" in plan2.goal.lower()
