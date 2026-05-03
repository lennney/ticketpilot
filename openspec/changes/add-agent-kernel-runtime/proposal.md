---
name: add-agent-kernel-runtime
author: len
status: proposed
created: 2026-05-03
---

# Proposal: Add Agent Kernel / Runtime

## Why

TicketPilot currently implements a linear 4-stage pipeline (intake → classify → risk → retrieve) with an optional draft generation step. While this works for straightforward tickets, it has no mechanism for:

- **Adaptive routing**: Choosing different processing paths based on ticket type (refund vs. complaint vs. account issue).
- **Tool composition**: Wrapping existing capabilities (classify, risk, retrieve, draft) as reusable, traceable, independently testable units.
- **Run-level orchestration**: A structured agent loop that can observe intermediate results and decide next steps.
- **Business skill organization**: Encapsulating domain-specific processing logic (e.g., refund workflows, complaint escalation) as documented, loadable skills rather than inline code.
- **Execution trace**: A single, unified trace of a complete agent run from ticket receipt to final decision, spanning all tool calls and routing decisions.

Adding a lightweight Agent Kernel / Runtime within TicketPilot transforms the project from a "linear pipeline" into an "agentic workflow" without breaking existing contracts, adding real LLM calls, or becoming a generic agent framework.

## What Changes

1. **New `src/ticketpilot/agent/` module** — contains the Agent Kernel runtime: schemas, tool registry, deterministic task planner, agent loop, skill loader, memory, and trace.

2. **New `skills/runtime/` directory** — business-level customer support skills (separate from `.claude/skills/` which are Claude Code development skills).

3. **Existing modules remain untouched** — the agent layer wraps, composes, and orchestrates existing pipeline, drafting, and review capabilities. It does not modify them.

4. **Optional workflow** — `run_agent_pipeline(raw_ticket)` as an alternative entrypoint alongside `intake_risk_pipeline()` and `run_pipeline_with_draft()`. Existing callers continue to work unchanged.

## Non-Goals

- NOT a general-purpose agent framework. No LangGraph, AutoGen, CrewAI, or multi-agent orchestration.
- NOT a Claude Code clone. No terminal execution, no code generation, no MCP.
- NOT a chatbot. The output is a structured ticket processing result, not conversational.
- NOT replacing existing pipeline, drafting, review, or evaluation modules.
- NOT introducing real LLM calls, real embedding providers, or external network calls.
- NOT adding auto-send capability. Human review remains mandatory for high-risk cases.
- NOT adding authentication, multi-user, or production deployment features.
- NOT adding Langfuse, Ragas, or external tracing services.

## User Value

- **Portfolio demonstration**: Shows agentic workflow design patterns (tool registry, task planning, skill loading, run-level tracing) in a controlled, deterministic project.
- **Architecture extension**: Proves that TicketPilot's module boundaries are clean enough to be wrapped by an agent runtime without modification.
- **Structured traceability**: A complete AgentRun trace makes debugging and evaluation more informative than the current scattered traces.
- **Business skill encapsulation**: Customer support domain knowledge (refund rules, complaint escalation, etc.) becomes loadable, testable, and documented skills rather than inline heuristics.
