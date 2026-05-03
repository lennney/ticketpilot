# Agent Kernel

## Overview

The Agent Kernel is a lightweight, deterministic orchestration layer within TicketPilot. It wraps existing pipeline capabilities as registered tools, provides a rule-based task planner, a documented skill system, and run-level execution tracing. The Agent Kernel transforms TicketPilot from a linear pipeline into an agentic workflow system without modifying any existing module.

### What the Agent Kernel Does

- Composes existing pipeline stages (normalize, classify, assess risk, retrieve evidence, draft) into a single `run_agent_pipeline()` call
- Provides a deterministic, keyword-based task planner that converts raw ticket text into structured plans
- Registers pipeline functions as named tools with metadata (risk level, I/O schema)
- Records append-only execution traces for every run
- Loads business skills from `skills/runtime/` for domain-specific routing
- Routes high-risk tickets to human review

### What the Agent Kernel Does NOT Do

- Does not auto-send draft replies (no event type or code path for sending)
- Does not call real LLM or embedding APIs (deterministic only)
- Does not make network calls
- Does not execute arbitrary code from skill definitions
- Does not modify any existing `src/ticketpilot/` module outside `agent/`
- Is not a general-purpose agent framework (no LangGraph, AutoGen, or CrewAI)

## Architecture

```
src/ticketpilot/agent/
├── __init__.py       # Public API exports
├── schemas.py        # Pydantic data contracts (AgentEvent, AgentRun, etc.)
├── trace.py          # Append-only event recording (AgentTrace)
├── registry.py       # Tool registry with callable binding (ToolRegistry)
├── tools.py          # 5 thin wrapper functions around existing pipeline code
├── planner.py        # Deterministic keyword-based planner (DeterministicTaskPlanner)
├── memory.py         # Working memory + episodic memory stores
├── loop.py           # run_agent_pipeline() entrypoint
└── skill_loader.py   # Skill loader for business skills

skills/runtime/
├── refund_request/       # Refund processing skill
├── complaint_escalation/  # Complaint/legal escalation skill (highest priority)
├── account_issue/        # Account security skill
└── technical_issue/      # Technical troubleshooting skill
```

## Core Components

### Agent Schemas (`schemas.py`)

Pydantic models defining all data contracts:

- **AgentEventType** — enum with 10 event types: `RUN_STARTED`, `PLAN_CREATED`, `SKILL_SELECTED`, `TOOL_CALLED`, `TOOL_RETURNED`, `DRAFT_GENERATED`, `RISK_CHECKED`, `HUMAN_REVIEW_REQUIRED`, `RUN_COMPLETED`, `RUN_FAILED`
- **AgentRunStatus** — enum with 5 statuses: `CREATED`, `RUNNING`, `COMPLETED`, `FAILED`, `HUMAN_REVIEW_REQUIRED`
- **AgentEvent** — single event with event_type, timestamp, step_number, data
- **AgentToolSpec** — tool descriptor with name, description, I/O schema, risk_level
- **AgentStep** — plan step with step_id, description, tool_name, input_params, fallback
- **AgentPlan** — structured plan with goal, constraints, steps, required_tools, success_criteria
- **AgentRun** — complete run record with run_id, events, plan, status, timestamps, results

### Trace (`trace.py`)

`AgentTrace` provides append-only event recording for a single run. Events are stored in insertion order and cannot be modified or deleted after being added. Supports JSON export via `to_json()` and `to_dict()`.

### Tool Registry (`registry.py`)

`ToolRegistry` maps tool names to `RegisteredTool` instances (dataclass combining `AgentToolSpec` with a callable handler). Supports register, lookup (`get`, `has`), listing (`list_names`, `list_specs`), and invocation (`call`). Duplicate names raise `ValueError`; unknown names raise `KeyError`.

### Tool Wrappers (`tools.py`)

Five thin adapter functions that convert dict input to the required Pydantic models, call existing pipeline logic, and return dict output:

| Tool | Risk Level | Input | Output |
|------|-----------|-------|--------|
| `normalize_ticket` | low | raw_ticket | NormalizedTicket dict |
| `classify_ticket` | low | normalized_text | ClassificationResult dict |
| `assess_risk` | medium | normalized_ticket, classification | RiskAssessment dict |
| `retrieve_evidence` | medium | normalized_text, intent, risk_flags, top_k | Evidence list + trace |
| `generate_draft` | high | ticket_output | DraftReply dict |

`create_default_tool_registry()` pre-populates a registry with all 5 tools at their correct risk levels.

### Deterministic Planner (`planner.py`)

`DeterministicTaskPlanner` uses keyword matching to select from 7 plan templates. Templates are checked in priority order, with `complaint_escalation` having highest priority to ensure legal/complaint tickets are always handled first. Unknown intent falls back to `generic_support`. Plans always consist of 5 core steps (normalize → classify → assess risk → retrieve evidence → generate draft).

### Memory (`memory.py`)

- **WorkingMemory** — per-run key-value store for intermediate step results. Isolated by run_id; no cross-run contamination.
- **EpisodicMemory** — append-only store of completed run records. Records are deep-copied on append; no update or delete methods exposed. `clear()` exists for test/reset only.

### Agent Loop (`loop.py`)

The `run_agent_pipeline(raw_ticket, registry, planner)` entrypoint composes all components into a single deterministic run:

1. Create run_id, AgentTrace, WorkingMemory
2. Create plan via DeterministicTaskPlanner
3. Execute 5 tool steps sequentially (normalize → classify → assess risk → retrieve evidence → generate draft)
4. Check risk + draft for human_review flags; route to `HUMAN_REVIEW_REQUIRED` if needed
5. Return AgentRun with complete trace, plan, results, and final status

### Skill Loader (`skill_loader.py`)

`SkillLoader` scans `skills/runtime/` directories and loads `SkillDefinition` objects (frozen dataclass) from `planner_template.yaml` + `SKILL.md`. Selection methods:

- `select_by_id(skill_id)` — direct lookup, returns fallback if unknown
- `select_by_issue_type(issue_type)` — first match by type
- `select_by_text(text)` — keyword matching with complaint-first priority, falls back to `generic_support`

Validation: checks required_tools against the known 5-tool set, detects duplicate skill_ids, and validates YAML structure. Malformed files raise `SkillLoadError` (never silently ignored).

## Data Flow

```
RawTicket
  │
  ▼
run_agent_pipeline()
  │
  ├── 1. AgentTrace created (RUN_STARTED)
  ├── 2. DeterministicTaskPlanner.create_plan() (PLAN_CREATED)
  ├── 3. normalize_ticket (TOOL_CALLED → TOOL_RETURNED)
  ├── 4. classify_ticket (TOOL_CALLED → TOOL_RETURNED)
  ├── 5. assess_risk (TOOL_CALLED → TOOL_RETURNED)
  ├── 6. retrieve_evidence (TOOL_CALLED → TOOL_RETURNED)
  ├── 7. generate_draft (TOOL_CALLED → TOOL_RETURNED → DRAFT_GENERATED)
  ├── 8. Risk check (RISK_CHECKED)
  ├── 9. Human review if needed (HUMAN_REVIEW_REQUIRED)
  └── 10. RUN_COMPLETED or RUN_FAILED
        │
        ▼
     AgentRun (with full event trace)
```

## Safety Constraints

1. **No auto-send**: AgentRun has no event type or code path for dispatching/sending. All skills state the no-auto-send constraint explicitly.
2. **No LLM/embedding calls**: All planning and tool execution is deterministic. No imports of LLM, embedding, or HTTP client libraries exist in the agent module.
3. **No network calls**: Tool wrappers call local pipeline code only.
4. **No arbitrary code execution**: Skill definitions are structured YAML + Markdown, never evaluated as code.
5. **Human review routing**: High-risk tickets (legal, compensation, privacy) route to `HUMAN_REVIEW_REQUIRED` status.

## Business Skills

Four business skills reside in `skills/runtime/`, each containing:
- `SKILL.md` — human-readable business recipe with constraints, evidence requirements, review rules, and bad cases
- `planner_template.yaml` — machine-readable plan data (skill_id, issue_type, goal, match_keywords, required_tools, steps)

| Skill | Issue Type | Priority | Key Keywords |
|-------|-----------|----------|-------------|
| refund_request | refund | Normal | 退款, 退钱, refund |
| complaint_escalation | complaint | Highest | 投诉, 起诉, compensation, complaint |
| account_issue | account | Normal | 账号, 登录, password, account |
| technical_issue | technical | Normal | 故障, 报错, bug, error |

## Test Coverage

- **203 agent unit tests** across 7 test files covering: schemas (39), trace (14), registry (17), tools (27), planner (33), memory (21), loop (25), skill loader (27)
- **34 agent integration tests** covering: refund flow, high-risk complaint flow, account security flow, cross-cutting concerns (event ordering, plan determinism, skill selection, no-evidence fallback, trace export, no auto-send)
- **119 total integration tests** (85 existing pipeline + 34 agent) with 0 skipped when DB is available
