---
name: agent-kernel
author: len
status: proposed
created: 2026-05-03
---

# Spec: Agent Kernel / Runtime

## Overview

The Agent Kernel is a lightweight, deterministic orchestration layer within TicketPilot. It wraps existing pipeline capabilities as registered tools, provides a rule-based task planner, a documented skill system, and run-level execution tracing. It transforms TicketPilot from a linear pipeline into an agentic workflow system without modifying any existing module.

## Core Requirements

### REQ-AGENT-01: Agent Run

The system MUST support a `run_agent_pipeline(raw_ticket)` entrypoint that:
1. Accepts a `RawTicket` as input.
2. Creates a structured AgentPlan.
3. Selects a business skill if applicable.
4. Executes steps by calling registered tools.
5. Observes and stores intermediate results in WorkingMemory.
6. Generates an evidence-grounded draft reply.
7. Performs a final risk check and routes to human review if required.
8. Records all events in an AgentTrace.
9. Returns an AgentRun with complete trace and status.

Rationale: Provides a single, structured entrypoint for agentic ticket processing that is distinct from both `intake_risk_pipeline()` and `run_pipeline_with_draft()`.

### REQ-AGENT-02: No Modification to Existing Modules

The Agent Kernel MUST NOT modify, patch, or monkey-patch any existing `src/ticketpilot/` module (pipeline, intake, classification, risk, retrieval, drafting, review, evaluation, schema). It MUST only import and call existing functions.

Rationale: Preserves backward compatibility. Existing callers, tests, and evaluation pipeline continue to work unchanged.

### REQ-AGENT-03: Tool Registry

The system MUST provide a ToolRegistry that:
1. Allows registering tools with: name, description, input_schema (JSON Schema dict), output_schema (JSON Schema dict), risk_level, and callable.
2. Requires unique tool names (duplicate registration raises an error).
3. Supports lookup by name, listing all tools, and checking tool existence.
4. Initially registers at least 5 tools: normalize_ticket, classify_ticket, assess_risk, retrieve_evidence, generate_draft.

Rationale: The registry makes tool composition explicit, inspectable, and independently testable. JSON Schema dicts for input/output enable future validation without coupling to Pydantic models.

### REQ-AGENT-04: Deterministic Task Planner

The system MUST provide a DeterministicTaskPlanner that:
1. Creates an AgentPlan from raw ticket text using rule-based keyword matching.
2. Supports at least 6 plan templates: refund, return_exchange, complaint_escalation, account_issue, logistics_query, and generic fallback.
3. Each template defines ordered steps with tool name, input params, and fallback.
4. The planner is deterministic: same input → same plan.

Rationale: Rule-based planning avoids LLM dependency and ensures predictable, testable behavior. Future LLM-based planning is out of scope.

### REQ-AGENT-05: Run-Level Trace

The system MUST provide AgentTrace that:
1. Records events in order with event type, timestamp, step number, and data payload.
2. Supports at least these event types: RUN_STARTED, PLAN_CREATED, SKILL_SELECTED, TOOL_CALLED, TOOL_RETURNED, DRAFT_GENERATED, RISK_CHECKED, HUMAN_REVIEW_REQUIRED, RUN_COMPLETED, RUN_FAILED.
3. Events are append-only (cannot be modified after recording).
4. Supports JSON export for audit and debugging.

Rationale: Structured trace enables debugging, portfolio demonstration, and future evaluation of agent behavior. No external tracing service required.

### REQ-AGENT-06: Working Memory

The system MUST provide WorkingMemory for per-run context that:
1. Stores intermediate results keyed by step_id.
2. Is isolated between runs (no cross-run contamination).
3. Stores: normalized_text, classification, risk_assessment, evidence_candidates, draft_reply, and arbitrary intermediate_results dict.

Rationale: Working memory replaces ad-hoc parameter passing and provides a single context store for the agent loop.

### REQ-AGENT-07: Episodic Memory (Lightweight)

The system MUST provide EpisodicMemory that:
1. Stores completed AgentRun records in an append-only list.
2. Supports query by run_id and listing all runs.
3. Optional JSONL persistence (same pattern as ReviewStore).
4. Enforces append-only: runs cannot be deleted or modified after addition.

Rationale: Enables post-run trace review and debugging without a database. Pattern mirrors ReviewStore's append-only JSONL design.

### REQ-AGENT-08: Runtime Skill System

The system MUST support runtime skills stored in `skills/runtime/` that:
1. Each skill is a directory with a `SKILL.md` definition file and an optional `planner_template.yaml`.
2. SKILL.md documents: when_to_use, required_tools, business_constraints, evidence_requirements, human_review_rules, bad_cases.
3. SkillLoader scans `skills/runtime/` and loads available skills.
4. The agent loop can select a skill based on the plan goal or ticket intent.
5. Skills are separate from `.claude/skills/` (Claude Code development skills).

Rationale: Business process knowledge becomes documented, loadable, and independently testable. Separating runtime skills from development skills prevents confusion.

### REQ-AGENT-09: Safety Constraints

The Agent Kernel MUST:
1. Never auto-send draft replies. The review console remains the sole output channel.
2. Never call external LLM or embedding APIs.
3. Never make network calls.
4. Never execute arbitrary code from skill definitions.
5. Route to human review when `must_human_review=True` (from risk assessment or draft).

Rationale: These safety constraints align with TicketPilot's existing architectural invariants.

## Non-Requirements

- The Agent Kernel is NOT a general-purpose agent framework.
- The Agent Kernel is NOT a chatbot or conversational system.
- The Agent Kernel is NOT a Claude Code clone.
- The Agent Kernel does NOT require LangGraph, AutoGen, CrewAI, or any orchestration framework.
- The Agent Kernel does NOT perform LLM-based planning or reasoning.
- The Agent Kernel does NOT support dynamic tool creation or code generation.
- The Agent Kernel does NOT replace existing pipeline, drafting, review, or evaluation modules.
- The Agent Kernel does NOT add authentication, multi-user, or deployment features.
- The Agent Kernel does NOT connect to external tracing services (Langfuse, Ragas, etc.).

## Data Contracts

See `design.md` for full Pydantic schema definitions. Key types:

- `AgentEventType` — enum with 10 event types
- `AgentEvent` — single trace event with type, timestamp, step_number, data
- `AgentTool` — registered tool descriptor with name, description, schemas, callable
- `AgentPlan` — structured plan with goal, constraints, steps, required_tools, success_criteria
- `AgentStep` — single step with tool reference and input params
- `AgentRun` — complete run record with all fields, events, and final status
- `WorkingMemory` — per-run mutable context store
- `EpisodicMemory` — append-only historical run store

## File Layout

```
src/ticketpilot/agent/          # New module — Agent Kernel runtime
├── __init__.py
├── schemas.py                  # Agent schemas (REQ-AGENT-01, 03, 04)
├── registry.py                 # ToolRegistry (REQ-AGENT-03)
├── planner.py                  # DeterministicTaskPlanner (REQ-AGENT-04)
├── loop.py                     # Agent loop entrypoint (REQ-AGENT-01)
├── memory.py                   # WorkingMemory + EpisodicMemory (REQ-AGENT-06, 07)
├── skill_loader.py             # SkillLoader (REQ-AGENT-08)
├── trace.py                    # AgentTrace (REQ-AGENT-05)
└── tools/                      # Tool wrappers (REQ-AGENT-03)
    ├── __init__.py
    ├── intake_tool.py
    ├── classify_tool.py
    ├── risk_tool.py
    ├── retrieve_tool.py
    └── draft_tool.py

skills/runtime/                 # Business skills (REQ-AGENT-08)
├── __init__.py
├── refund_request/
├── complaint_escalation/
├── account_issue/
└── technical_issue/

tests/unit/test_agent_*.py      # Unit tests for all agent modules
tests/integration/test_agent_runtime.py  # Integration tests
docs/technical/agent_kernel.md  # Technical documentation
```
