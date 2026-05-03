---
name: add-agent-kernel-runtime
author: len
status: active
created: 2026-05-03
---

# Tasks: Agent Kernel / Runtime

## Phase 0 — Planning and OpenSpec Design (this phase, already done)

- [x] 0.1 Read existing project structure (src, tests, docs, openspec, .claude)
- [x] 0.2 Identify integration points and boundaries
- [x] 0.3 Create `openspec/changes/add-agent-kernel-runtime/` with proposal, design, tasks, spec
- [x] 0.4 Define batch structure, allowed/forbidden files, and acceptance criteria

## Phase 1 — Agent Schemas and Trace Event Models ✅

- [x] 1.1 Create `src/ticketpilot/agent/__init__.py` with public API exports
- [x] 1.2 Create `src/ticketpilot/agent/schemas.py`
- [x] 1.3 Create `src/ticketpilot/agent/trace.py`
- [x] 1.4 Create `tests/unit/test_agent_schemas.py`
- [x] 1.5 Create `tests/unit/test_agent_trace.py`

### Allowed files
- `src/ticketpilot/agent/__init__.py` (new)
- `src/ticketpilot/agent/schemas.py` (new)
- `src/ticketpilot/agent/trace.py` (new)
- `tests/unit/test_agent_schemas.py` (new)
- `tests/unit/test_agent_trace.py` (new)

### Forbidden files
- Any existing `src/ticketpilot/` module except the new `agent/` directory
- Any existing `tests/` file
- `skills/runtime/` (Phase 4)
- `docs/` except changelog/phase_status at Phase 6

### Acceptance criteria
- All agent schemas construct and validate correctly
- AgentEvent ordering is enforced
- AgentRun can be created with no plan (initial state)
- JSON serialization round-trips
- 100% unit test pass rate on new tests
- No existing src/ or tests/ files modified

## Phase 2 — Tool Registry and Tool Wrappers ✅

- [x] 2.1 Create `src/ticketpilot/agent/registry.py` — ToolRegistry + RegisteredTool
- [x] 2.2 Create `src/ticketpilot/agent/tools.py` — 5 wrapper functions + create_default_tool_registry()
- [x] 2.3 Update `src/ticketpilot/agent/__init__.py` — add Batch 2 exports
- [x] 2.4 Create `tests/unit/test_agent_registry.py` — 17 tests
- [x] 2.5 Create `tests/unit/test_agent_tools.py` — 27 tests

### Allowed files
- `src/ticketpilot/agent/__init__.py` (modified — exports only)
- `src/ticketpilot/agent/registry.py` (new)
- `src/ticketpilot/agent/tools.py` (new)
- `tests/unit/test_agent_registry.py` (new)
- `tests/unit/test_agent_tools.py` (new)

### Forbidden
- Modifying existing src/ or tests/ files
- Calling real LLM or embedding providers
- Network calls in tool wrappers

## Phase 3 — Task Planner + Agent Loop ✅

- [x] 3.1 Create `src/ticketpilot/agent/planner.py`
- [x] 3.2 Create `src/ticketpilot/agent/memory.py`
- [x] 3.3 Create `src/ticketpilot/agent/loop.py`
- [x] 3.4 Update `src/ticketpilot/agent/__init__.py` to add Batch 3 exports
- [x] 3.5 Create `tests/unit/test_agent_planner.py` — 33 tests
- [x] 3.6 Create `tests/unit/test_agent_memory.py` — 21 tests
- [x] 3.7 Create `tests/unit/test_agent_loop.py` — 25 tests

### Allowed files
- `src/ticketpilot/agent/planner.py` (new)
- `src/ticketpilot/agent/memory.py` (new)
- `src/ticketpilot/agent/loop.py` (new)
- `src/ticketpilot/agent/__init__.py` (modified — exports only)
- `tests/unit/test_agent_planner.py` (new)
- `tests/unit/test_agent_memory.py` (new)
- `tests/unit/test_agent_loop.py` (new)

## Phase 4 — Runtime Skill Loader + Business Skills

- [ ] 4.1 Create `skills/runtime/__init__.py`
- [ ] 4.2 Create `src/ticketpilot/agent/skill_loader.py`:
  - Load skill definitions from `skills/runtime/*/SKILL.md`
  - Parse YAML frontmatter or structured format
  - Skill selection based on plan goal or intent
- [ ] 4.3 Create initial skills:
  - `skills/runtime/refund_request/SKILL.md` + `planner_template.yaml`
  - `skills/runtime/complaint_escalation/SKILL.md` + `planner_template.yaml`
  - `skills/runtime/account_issue/SKILL.md` + `planner_template.yaml`
  - `skills/runtime/technical_issue/SKILL.md` + `planner_template.yaml`
- [ ] 4.4 Update agent loop to integrate skill selection
- [ ] 4.5 Create `tests/unit/test_agent_skill_loader.py`:
  - Skill loading from directory
  - Skill selection by intent/plan
  - Missing skill fallback

### Allowed files
- `skills/runtime/` (new directory + files)
- `src/ticketpilot/agent/skill_loader.py` (new)
- `tests/unit/test_agent_skill_loader.py` (new)

## Phase 5 — Integration Tests

- [ ] 5.1 Create `tests/integration/test_agent_runtime.py`:
  - Full agent run through real pipeline (DB required for retrieval)
  - AgentRun shape: ticket_id, plan, events, final_status
  - Event ordering: RUN_STARTED → PLAN_CREATED → TOOL_CALLED → ... → RUN_COMPLETED
  - Human review routing for high-risk tickets
  - Fallback for no-evidence tickets
  - Trace export structure

### Allowed files
- `tests/integration/test_agent_runtime.py` (new)

## Phase 6 — Documentation, Changelog, Quality Gate, Archive

- [ ] 6.1 Create `docs/technical/agent_kernel.md` — design doc for the agent module
- [ ] 6.2 Update `docs/changelog.md` with all batch entries
- [ ] 6.3 Update `docs/phase_status.md` — add Agent Kernel entry mark ACCEPTED
- [ ] 6.4 Run full quality gate (Ruff, unit tests, integration tests, coverage, OpenSpec)
- [ ] 6.5 Archive OpenSpec change
- [ ] 6.6 Post-archive validation

### Allowed files
- `docs/technical/agent_kernel.md` (new)
- `docs/changelog.md` (update)
- `docs/phase_status.md` (update)
- `openspec/changes/add-agent-kernel-runtime/` (update tasks)

### Acceptance criteria (final)
- All unit tests pass (existing 433 + new agent tests)
- All integration tests pass (existing 85 + new agent integration tests)
- 0 skipped integration tests
- Coverage ≥ 70% (new agent code must have adequate coverage)
- Ruff clean
- OpenSpec validate --all passes
- Secret scan clean
- Working tree clean
- No existing src/ or tests/ files modified outside agent module
- No real LLM, real embedding, network calls, auto-send, or generic agent framework
