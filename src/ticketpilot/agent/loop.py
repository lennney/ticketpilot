"""Agent runtime loop — composes trace, planner, registry, and working memory."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from ticketpilot.agent.memory import WorkingMemory
from ticketpilot.agent.planner import DeterministicTaskPlanner
from ticketpilot.agent.registry import ToolRegistry
from ticketpilot.agent.schemas import (
    AgentEventType,
    AgentPlan,
    AgentRun,
    AgentRunStatus,
)
from ticketpilot.agent.tools import create_default_tool_registry
from ticketpilot.agent.trace import AgentTrace
from ticketpilot.schema.ticket import RawTicket


def _construct_ticket_output(
    run_id: str,
    raw_ticket: RawTicket | dict[str, Any],
    normalized_ticket: dict[str, Any],
    classification: dict[str, Any],
    risk_assessment: dict[str, Any],
    evidence_result: dict[str, Any],
) -> dict[str, Any]:
    """Build a TicketOutput-compatible dict from step results.

    The dict is consumed by generate_draft_tool which converts it
    back to a TicketOutput Pydantic model internally.
    """
    raw_dict = (
        raw_ticket.model_dump(mode="json")
        if isinstance(raw_ticket, RawTicket)
        else raw_ticket
    )
    return {
        "ticket_id": run_id,
        "raw_ticket": raw_dict,
        "normalized_ticket": normalized_ticket,
        "classification": classification,
        "risk_assessment": risk_assessment,
        "output_at": datetime.now(timezone.utc).isoformat(),
        "evidence_candidates": evidence_result.get("evidence_candidates", []),
        "retrieval_trace": evidence_result.get("retrieval_trace"),
    }


def run_agent_pipeline(
    raw_ticket: RawTicket,
    registry: ToolRegistry | None = None,
    planner: DeterministicTaskPlanner | None = None,
) -> AgentRun:
    """Execute the agent pipeline for a raw ticket.

    Composes trace, planner, registry, and working memory into a single
    deterministic run.  All tool calls go through the provided (or default)
    ToolRegistry.

    Args:
        raw_ticket: The raw ticket to process.
        registry:  Tool registry to use. Falls back to create_default_tool_registry().
        planner:   Task planner to use. Falls back to DeterministicTaskPlanner().

    Returns:
        AgentRun with full trace, plan, and final status.
    """
    run_id = str(uuid.uuid4())
    trace = AgentTrace(run_id)
    wm = WorkingMemory(run_id)
    reg = registry or create_default_tool_registry()
    plan_engine = planner or DeterministicTaskPlanner()

    started_at = datetime.now(timezone.utc)
    trace.add_event(AgentEventType.RUN_STARTED)

    ticket_output: dict[str, Any] | None = None
    draft_reply: dict[str, Any] | None = None
    plan: AgentPlan | None = None

    try:
        # --- plan ---
        text = raw_ticket.original_text if isinstance(raw_ticket, RawTicket) else str(raw_ticket)
        plan = plan_engine.create_plan(text)
        trace.add_event(AgentEventType.PLAN_CREATED, data={"template": plan_engine.select_template(text)})
        wm.set("plan", plan)

        # --- execute 5 core steps ---
        step_results: dict[str, dict[str, Any]] = {}

        # Step 1: normalize_ticket
        trace.add_event(AgentEventType.TOOL_CALLED, data={"tool": "normalize_ticket", "step": "s1_normalize"})
        norm_result = reg.call("normalize_ticket", {"raw_ticket": raw_ticket})
        trace.add_event(AgentEventType.TOOL_RETURNED, data={"tool": "normalize_ticket"})
        wm.set("normalized_ticket", norm_result)
        step_results["normalize_ticket"] = norm_result

        # Step 2: classify_ticket
        trace.add_event(AgentEventType.TOOL_CALLED, data={"tool": "classify_ticket", "step": "s2_classify"})
        cls_result = reg.call("classify_ticket", {"normalized_text": norm_result["text"]})
        trace.add_event(AgentEventType.TOOL_RETURNED, data={"tool": "classify_ticket"})
        wm.set("classification", cls_result)
        step_results["classify_ticket"] = cls_result

        # Step 3: assess_risk
        trace.add_event(AgentEventType.TOOL_CALLED, data={"tool": "assess_risk", "step": "s3_assess_risk"})
        risk_result = reg.call("assess_risk", {
            "normalized_ticket": norm_result,
            "classification": cls_result,
        })
        trace.add_event(AgentEventType.TOOL_RETURNED, data={"tool": "assess_risk"})
        wm.set("risk_assessment", risk_result)
        step_results["assess_risk"] = risk_result

        # Step 4: retrieve_evidence
        trace.add_event(AgentEventType.TOOL_CALLED, data={"tool": "retrieve_evidence", "step": "s4_retrieve_evidence"})
        ev_result = reg.call("retrieve_evidence", {
            "normalized_text": norm_result["text"],
            "intent": cls_result["intent"],
            "risk_flags": risk_result["flags"],
            "top_k": 10,
        })
        trace.add_event(AgentEventType.TOOL_RETURNED, data={"tool": "retrieve_evidence"})
        wm.set("evidence_result", ev_result)
        step_results["retrieve_evidence"] = ev_result

        # Build ticket_output for generate_draft
        ticket_output = _construct_ticket_output(
            run_id, raw_ticket, norm_result, cls_result, risk_result, ev_result,
        )
        wm.set("ticket_output", ticket_output)

        # Step 5: generate_draft
        trace.add_event(AgentEventType.TOOL_CALLED, data={"tool": "generate_draft", "step": "s5_generate_draft"})
        draft_reply = reg.call("generate_draft", {"ticket_output": ticket_output})
        trace.add_event(AgentEventType.TOOL_RETURNED, data={"tool": "generate_draft"})
        wm.set("draft_reply", draft_reply)

        trace.add_event(AgentEventType.DRAFT_GENERATED, data={
            "confidence": draft_reply.get("confidence"),
            "must_human_review": draft_reply.get("must_human_review"),
        })

        # --- final status ---
        risk_must_review = risk_result.get("must_human_review", False)
        draft_must_review = draft_reply.get("must_human_review", False)
        needs_review = risk_must_review or draft_must_review

        if needs_review:
            trace.add_event(AgentEventType.HUMAN_REVIEW_REQUIRED, data={
                "reason": "risk" if risk_must_review else "draft",
            })
            final_status = AgentRunStatus.HUMAN_REVIEW_REQUIRED
        else:
            final_status = AgentRunStatus.COMPLETED

        trace.add_event(AgentEventType.RISK_CHECKED, data={
            "must_human_review": needs_review,
            "final_status": final_status.value,
        })
        trace.add_event(AgentEventType.RUN_COMPLETED)
        completed_at = datetime.now(timezone.utc)

    except Exception as exc:
        trace.add_event(AgentEventType.RUN_FAILED, data={"error": str(exc)})
        final_status = AgentRunStatus.FAILED
        completed_at = datetime.now(timezone.utc)

    return AgentRun(
        run_id=run_id,
        raw_ticket_text=raw_ticket.original_text if isinstance(raw_ticket, RawTicket) else str(raw_ticket),
        plan=plan,
        skill_id=None,
        events=trace.get_events(),
        ticket_output=ticket_output,
        draft_reply=draft_reply,
        review_decision=None,
        final_status=final_status,
        started_at=started_at,
        completed_at=completed_at,
    )
