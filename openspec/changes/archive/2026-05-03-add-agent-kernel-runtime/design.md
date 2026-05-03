---
name: add-agent-kernel-runtime
author: len
status: proposed
created: 2026-05-03
---

# Design: Agent Kernel / Runtime

## Architecture Overview

The Agent Kernel adds an orchestration layer above the existing pipeline without modifying it:

```
RawTicket
    │
    ▼
┌──────────────────────────────────────────────────┐
│                  Agent Runtime                     │
│                                                    │
│  ┌──────────┐   ┌────────────┐   ┌───────────┐   │
│  │ Task     │   │ Tool       │   │ Skill     │   │
│  │ Planner  │──▶│ Registry   │──▶│ Loader    │   │
│  └──────────┘   └────────────┘   └───────────┘   │
│       │               │               │           │
│       ▼               ▼               ▼           │
│  ┌──────────────────────────────────────────┐     │
│  │            Agent Loop                     │     │
│  │  Plan → Select Skill → Call Tools →      │     │
│  │  Observe → Draft → Risk Check → Done     │     │
│  └──────────────────────────────────────────┘     │
│       │                                            │
│       ▼                                            │
│  ┌──────────────────────────────────────────┐     │
│  │         Run-level Trace                   │     │
│  │  (events: Plan, SkillSelect, ToolCall,   │     │
│  │   ToolResult, Draft, Risk, Review, Done) │     │
│  └──────────────────────────────────────────┘     │
│       │                                            │
│       ▼                                            │
│  ┌──────────────────────────────────────────┐     │
│  │         WorkingMemory / EpisodicMemory    │     │
│  └──────────────────────────────────────────┘     │
└──────────────────────┬───────────────────────────┘
                       │
                       ▼
    (composes existing modules below — untouched)
                       │
                       ▼
    intake_risk_pipeline()  →  generate_draft()
                       │
                       ▼
              review_console / ReviewDecision
```

## Module Structure

```
src/ticketpilot/agent/
├── __init__.py              # Public API: run_agent_pipeline()
├── schemas.py               # AgentRun, AgentPlan, AgentStep, AgentEvent, etc.
├── registry.py              # ToolRegistry — wraps existing capabilities as tools
├── planner.py               # DeterministicTaskPlanner — rule-based plan creation
├── loop.py                  # AgentLoop — plan → execute → observe → complete
├── skill_loader.py          # SkillLoader — loads skills/runtime/ SKILL.md files
├── memory.py                # WorkingMemory, EpisodicMemory (lightweight)
├── trace.py                 # AgentTrace — run-level event recording and export
└── tools/
    ├── __init__.py          # Tool registration helpers
    ├── intake_tool.py       # Wrapper: intake_pipeline
    ├── classify_tool.py     # Wrapper: IntentClassifier
    ├── risk_tool.py         # Wrapper: RiskAssessor
    ├── retrieve_tool.py     # Wrapper: retrieve_evidence
    └── draft_tool.py        # Wrapper: generate_draft
```

## Data Contracts (Pydantic)

### AgentEvent — single step event in the run trace

```python
class AgentEventType(str, Enum):
    RUN_STARTED = "run_started"
    PLAN_CREATED = "plan_created"
    SKILL_SELECTED = "skill_selected"
    TOOL_CALLED = "tool_called"
    TOOL_RETURNED = "tool_returned"
    DRAFT_GENERATED = "draft_generated"
    RISK_CHECKED = "risk_checked"
    HUMAN_REVIEW_REQUIRED = "human_review_required"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"

class AgentEvent(BaseModel):
    event_type: AgentEventType
    timestamp: datetime
    step_number: int | None = None
    data: dict = Field(default_factory=dict)  # event-specific payload
```

### AgentTool — registered capability

```python
class AgentTool(BaseModel):
    name: str                     # e.g. "classify_ticket"
    description: str              # human-readable description
    input_schema: dict            # JSON Schema for expected input
    output_schema: dict           # JSON Schema for expected output
    risk_level: str               # "none" | "low" | "medium" | "high"
    callable: Callable            # the wrapped function
```

### AgentPlan — structured task plan

```python
class AgentPlan(BaseModel):
    goal: str                     # what the agent is trying to accomplish
    constraints: list[str]        # e.g. ["must_human_review_if_high_risk"]
    steps: list[AgentStep]        # ordered execution steps
    required_tools: list[str]     # tools needed for this plan
    success_criteria: list[str]   # how to determine success
```

### AgentStep — single step within a plan

```python
class AgentStep(BaseModel):
    step_id: str
    description: str
    tool: str                     # tool name to call
    input_params: dict            # parameters for the tool
    expected_output: str | None   # optional description
    fallback: str | None          # fallback description
```

### AgentRun — complete run record

```python
class AgentRun(BaseModel):
    run_id: str
    raw_ticket: RawTicket
    plan: AgentPlan | None
    skill_id: str | None
    events: list[AgentEvent]
    ticket_output: TicketOutput | None
    draft_reply: DraftReply | None
    review_decision: ReviewDecision | None
    final_status: str              # "completed" | "failed" | "human_review_required"
    started_at: datetime
    completed_at: datetime | None
```

### WorkingMemory — single-run context

```python
class WorkingMemory(BaseModel):
    run_id: str
    normalized_text: str = ""
    classification: ClassificationResult | None = None
    risk_assessment: RiskAssessment | None = None
    evidence_candidates: list[EvidenceCandidate] = Field(default_factory=list)
    draft_reply: DraftReply | None = None
    intermediate_results: dict[str, Any] = Field(default_factory=dict)
```

### EpisodicMemory — historical run records (lightweight)

```python
class EpisodicMemory(BaseModel):
    """Append-only store of past agent runs for trace queries."""
    runs: list[AgentRun] = Field(default_factory=list)

    def add(self, run: AgentRun) -> None: ...
    def get_by_id(self, run_id: str) -> AgentRun | None: ...
    def get_all(self) -> list[AgentRun]: ...
```

## Tool Registry Design

The ToolRegistry wraps existing TicketPilot capabilities without modifying them:

| Tool Name | Wraps | Input | Output |
|-----------|-------|-------|--------|
| `normalize_ticket` | `intake_pipeline()` | RawTicket | NormalizedTicket |
| `classify_ticket` | `IntentClassifier.classify()` | str | ClassificationResult |
| `assess_risk` | `RiskAssessor.assess()` | NormalizedTicket + ClassificationResult | RiskAssessment |
| `retrieve_evidence` | `retrieve_evidence()` | normalized_text + intent + risk_flags | list[EvidenceCandidate] + RetrievalTrace |
| `generate_draft` | `generate_draft()` | TicketOutput | DraftReply |
| `check_citations` | `CitationValidator.validate()` | draft_text + citations + evidence | validation result |

## Deterministic Task Planner

The planner is rule-based, not LLM-based:

```
Input: RawTicket (original_text)
Output: AgentPlan

Logic:
1. Check original_text for known keyword patterns.
2. Match to a pre-defined plan template by ticket type.
3. Fall back to a generic plan for unknown types.

Plan Templates (initial set):
- refund_request: normalize → classify → risk → retrieve(FAQ+Policy) → draft → risk_check
- return_exchange: normalize → classify → risk → retrieve(FAQ+Policy) → draft → risk_check
- complaint_escalation: normalize → classify → risk(extended) → retrieve(Policy+Case) → draft(escalation) → risk_check → human_review
- account_issue: normalize → classify → risk(security) → retrieve(FAQ+Policy) → draft → risk_check
- logistics_query: normalize → classify → risk → retrieve(FAQ) → draft → risk_check
- generic: normalize → classify → risk → retrieve → draft → risk_check
```

## Skill Organization

Skills are business-level processing recipes stored as YAML/Markdown in `skills/runtime/`:

```
skills/runtime/
├── __init__.py
├── loader.py                  # Code that reads skill definitions
├── refund_request/
│   ├── SKILL.md               # When to use, required tools, constraints
│   └── planner_template.yaml  # Plan template for refund tickets
├── complaint_escalation/
│   ├── SKILL.md
│   └── planner_template.yaml
├── account_issue/
│   ├── SKILL.md
│   └── planner_template.yaml
└── technical_issue/
    ├── SKILL.md
    └── planner_template.yaml
```

Each SKILL.md contains:
- `when_to_use` — keyword/intent triggers
- `required_tools` — which tools this skill needs
- `business_constraints` — domain rules (e.g., "refund must check policy first")
- `evidence_requirements` — which doc types to search
- `human_review_rules` — when to force human review
- `bad_cases` — known failure scenarios

## Agent Loop Pseudocode

```
def run_agent_pipeline(raw_ticket: RawTicket) -> AgentRun:
    run = AgentRun(run_id=uuid4(), raw_ticket=raw_ticket, events=[])
    emit(RUN_STARTED)

    working_memory = WorkingMemory(run_id=run.run_id)

    # 1. Task Planning
    plan = planner.create_plan(raw_ticket.original_text)
    run.plan = plan
    emit(PLAN_CREATED, plan=plan)

    # 2. Skill Selection
    skill = skill_loader.select_skill(plan)
    run.skill_id = skill.id if skill else None
    emit(SKILL_SELECTED, skill_id=skill.id if skill else "none")

    # 3. Execute Steps
    for step in plan.steps:
        tool = registry.get(step.tool)
        emit(TOOL_CALLED, tool=step.tool, params=step.input_params)
        try:
            result = tool.callable(**step.input_params)
            working_memory.intermediate_results[step.step_id] = result
            emit(TOOL_RETURNED, tool=step.tool, result_preview=str(result)[:200])
        except Exception as e:
            emit(RUN_FAILED, error=str(e))
            run.final_status = "failed"
            return run

    # 4. Assemble TicketOutput from working memory
    ticket_output = build_ticket_output(working_memory, raw_ticket)
    run.ticket_output = ticket_output

    # 5. Generate Draft
    draft = generate_draft(ticket_output)
    run.draft_reply = draft
    emit(DRAFT_GENERATED, confidence=draft.confidence, fallback=draft.fallback_reason)

    # 6. Risk Check
    if draft.must_human_review or ticket_output.risk_assessment.must_human_review:
        emit(HUMAN_REVIEW_REQUIRED,
             reason="high_risk_or_unsupported_claims")
        run.final_status = "human_review_required"
    else:
        run.final_status = "completed"

    emit(RUN_COMPLETED, status=run.final_status)
    run.completed_at = datetime.utcnow()

    # 7. Record in episodic memory
    episodic_memory.add(run)

    return run
```

## File Boundaries

### Allowed to create
- `src/ticketpilot/agent/` (entire new module)
- `skills/runtime/` (entire new directory)
- `tests/unit/test_agent_*.py` (new test files)
- `tests/integration/test_agent_*.py` (new test files)
- `docs/technical/agent_kernel.md` (new doc)

### Allowed to modify
- `docs/changelog.md` (batch entries)
- `docs/phase_status.md` (status updates)
- `openspec/changes/add-agent-kernel-runtime/` (OpenSpec files)
- `pyproject.toml` (only if new lightweight dependencies are needed — unlikely)

### Forbidden to modify
- `src/ticketpilot/pipeline.py`
- `src/ticketpilot/intake/`
- `src/ticketpilot/classification/`
- `src/ticketpilot/risk/`
- `src/ticketpilot/retrieval/`
- `src/ticketpilot/drafting/`
- `src/ticketpilot/review/`
- `src/ticketpilot/evaluation/`
- `src/ticketpilot/schema/`
- `tests/unit/` (existing test files)
- `tests/integration/` (existing test files)
- `scripts/`
- `data/`

## Testing Strategy

### Unit tests
- Agent schemas: construction, validation, serialization
- Tool registry: registration, lookup, call wrapping
- Deterministic planner: plan creation, plan templates, fallback
- Skill loader: load skill defs, select skill
- WorkingMemory: read/write, isolation between runs
- EpisodicMemory: add, query, append-only invariant
- Agent trace: event recording, event ordering, export

### Integration tests
- Full agent run: raw_ticket → AgentRun with all events
- Agent run through existing pipeline (DB required for retrieval)
- Tool registry wrapping real pipeline functions
- EpisodicMemory persistence to JSONL

### What NOT to test
- No real LLM calls
- No network calls
- No real embedding quality
- No multi-agent coordination

## Risks and Limitations

1. **No real LLM** — The agent loop's "intelligence" is purely deterministic (rule-based planner, template-based drafting). The agentic workflow demonstrates architecture, not autonomous reasoning.
2. **Seed data only** — Skill templates and plan templates are based on 36 seed documents and 10 eval tickets. Not representative of real enterprise variety.
3. **Fake embeddings** — Tool-level retrieval uses fake embeddings; quality is pipeline-verification-only.
4. **Skill loader is YAML-based** — Skills are static definitions, not learned from data. No skill learning or optimization.
5. **EpisodicMemory is JSONL** — Not a database. Query capabilities are basic (by run_id or iterate all). No aggregation, no analytics.
6. **Scope creep risk** — The agent module must remain a lightweight wrapper. If it becomes a general-purpose agent framework, the change should be rejected.
7. **No production claims** — This is a local demo enhancement, not a production agent system.
