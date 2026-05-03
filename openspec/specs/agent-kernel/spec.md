# agent-kernel Specification

## Purpose
TBD - created by archiving change add-agent-kernel-runtime. Update Purpose after archive.
## Requirements
### Requirement: Agent Run Entrypoint
The system SHALL provide a `run_agent_pipeline(raw_ticket)` entrypoint that creates a structured AgentPlan, executes registered tool steps, stores intermediate results in WorkingMemory, generates an evidence-grounded draft reply, performs a final risk check with human review routing, and returns an AgentRun with complete trace and status.

#### Scenario: Normal refund ticket produces complete AgentRun
- WHEN `run_agent_pipeline()` is called with a refund ticket
- THEN it returns an AgentRun with run_id, plan, events, and final_status=RUN_COMPLETED

#### Scenario: Event ordering is maintained
- WHEN a pipeline run completes
- THEN events appear in order: RUN_STARTED before PLAN_CREATED before TOOL_CALLED before terminal event

#### Scenario: High-risk ticket routes to human review
- WHEN a ticket with legal or compensation risk flags is processed
- THEN the AgentRun final status indicates human review required

### Requirement: Agent Schemas and Trace
The system SHALL define Pydantic schemas for AgentEventType (10 event types), AgentRunStatus (5 statuses), AgentEvent, AgentToolSpec, AgentStep, AgentPlan, AgentRun, and an AgentTrace class with append-only event recording and JSON export.

#### Scenario: All schemas construct and validate correctly
- WHEN each schema is constructed with valid data
- THEN validation passes and field values are preserved

#### Scenario: AgentRun exists with no plan
- WHEN an AgentRun is created with plan=None
- THEN it represents an initial state before planning

#### Scenario: JSON serialization round-trips
- WHEN an AgentRun is serialized to JSON and deserialized
- THEN all fields are preserved

#### Scenario: AgentTrace is append-only
- WHEN an event is appended to a trace
- THEN it cannot be modified after recording

### Requirement: Tool Registry
The system SHALL provide a ToolRegistry that registers tools with unique names, descriptions, JSON Schema dicts, risk levels, and callables, and supports lookup, listing, existence checks, and invocation.

#### Scenario: Register and retrieve a tool
- WHEN a tool is registered with a unique name
- THEN it can be retrieved by name and listed

#### Scenario: Duplicate tool name raises error
- WHEN two tools are registered with the same name
- THEN a ValueError is raised

#### Scenario: At least 5 tools registered
- WHEN the default registry is created
- THEN normalize_ticket, classify_ticket, assess_risk, retrieve_evidence, and generate_draft are available

### Requirement: Deterministic Task Planner
The system SHALL provide a DeterministicTaskPlanner that creates AgentPlan objects from raw ticket text using rule-based keyword matching, supporting at least 6 plan templates with deterministic output.

#### Scenario: Same input produces same plan
- WHEN the planner is called twice with the same ticket text
- THEN the same plan is produced

#### Scenario: Complaint keyword has highest priority
- WHEN a ticket text contains both complaint and refund keywords
- THEN the complaint template is selected

#### Scenario: Unknown intent returns generic fallback
- WHEN a ticket text matches no business template
- THEN the generic fallback template is returned

### Requirement: Working Memory
The system SHALL provide WorkingMemory for per-run context storage of intermediate results keyed by step_id, isolated between runs.

#### Scenario: Store and retrieve intermediate result
- WHEN a result is stored by step_id
- THEN it can be retrieved by the same key

#### Scenario: No cross-run contamination
- WHEN a second run stores data
- THEN the first run's data is not visible in the second run

### Requirement: Episodic Memory
The system SHALL provide EpisodicMemory as an append-only store of completed AgentRun records, supporting query by run_id and listing all runs.

#### Scenario: Append and retrieve a run
- WHEN a completed AgentRun is appended
- THEN it can be retrieved by run_id

#### Scenario: Runs are append-only
- WHEN a run is added to EpisodicMemory
- THEN it cannot be deleted or modified

### Requirement: Runtime Skill Loader
The system SHALL provide a SkillLoader that scans `skills/runtime/` directories, loads SkillDefinition objects from `planner_template.yaml` and `SKILL.md`, validates required_tools against a known tool set, detects duplicate skill_ids, and provides deterministic selection by skill_id, issue_type, or keyword text matching with a safe fallback.

#### Scenario: Load 4 business skills
- WHEN SkillLoader.load_all() scans skills/runtime/
- THEN it returns 4 SkillDefinition objects with IDs: refund_request, complaint_escalation, account_issue, technical_issue

#### Scenario: Select skill by text keyword
- WHEN select_by_text() is called with a matching keyword
- THEN the corresponding skill is returned

#### Scenario: Unknown skill returns fallback
- WHEN select_by_id() is called with a nonexistent skill_id
- THEN the generic_support fallback skill is returned

#### Scenario: Malformed YAML raises SkillLoadError
- WHEN a skill directory contains invalid YAML
- THEN SkillLoadError is raised

#### Scenario: Unknown required_tool raises SkillLoadError
- WHEN a planner_template.yaml references an unknown tool
- THEN SkillLoadError is raised describing the unknown tool

#### Scenario: Duplicate skill_id raises SkillLoadError
- WHEN two skill directories declare the same skill_id
- THEN SkillLoadError is raised

### Requirement: Business Skills
The system SHALL provide 4 business skills in `skills/runtime/` each containing a `planner_template.yaml` (machine-readable) and `SKILL.md` (human-readable business recipe) documenting business constraints, evidence requirements, human review rules, and bad cases.

#### Scenario: Refund skill has refund keywords
- WHEN the refund_request skill is loaded
- THEN its match_keywords include Chinese and English refund terms

#### Scenario: Complaint skill has highest matching priority
- WHEN select_by_text() is called with text containing both complaint and refund keywords
- THEN complaint_escalation skill is returned

#### Scenario: Account skill has security keywords
- WHEN the account_issue skill is loaded
- THEN its match_keywords include account and login terms

#### Scenario: Technical skill has error keywords
- WHEN the technical_issue skill is loaded
- THEN its match_keywords include bug and error terms

### Requirement: No Modification to Existing Modules
The Agent Kernel SHALL NOT modify, patch, or monkey-patch any existing `src/ticketpilot/` module outside the `agent/` directory.

#### Scenario: Existing pipeline tests pass unchanged
- WHEN all existing unit and integration tests are run
- THEN they pass without modification

### Requirement: Safety Constraints
The Agent Kernel SHALL: (1) never auto-send draft replies, (2) never call external LLM or embedding APIs, (3) never make network calls, (4) never execute arbitrary code from skill definitions, (5) route to human review when must_human_review is True.

#### Scenario: No auto-send capability exists
- WHEN the agent kernel code is inspected
- THEN there is no code path that sends or dispatches draft replies

#### Scenario: No LLM or external API dependencies
- WHEN the agent kernel dependencies are inspected
- THEN there are no imports of LLM, embedding, or HTTP client libraries

