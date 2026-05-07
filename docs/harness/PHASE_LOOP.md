# Controller Phase Loop -- TicketPilot

## Purpose

Defines the 7-step workflow for executing one phase (a logical unit of work from tasks.md).
One phase = one loop cycle. Controller orchestrates; roles delegate execution.

This document extends AGENTS.md, not replaces it. It operationalizes:
- Section 11 (Controller Autonomy Rules)
- Section 12 (Controller Context Rules)
- Section 15 (Context Compression Handoff Rules)

---

## Phase Loop Diagram

```
+-----------------------------------------------------------------------+
|                         PHASE LOOP (7 steps)                          |
+-----------------------------------------------------------------------+
|                                                                       |
|  [1] PLANNER                                                          |
|      Creates/modifies plan for the phase                             |
|      Input: phase goal from tasks.md, previous phase results         |
|      Output: step-by-step plan with acceptance criteria               |
|      v                                                                 |
|  [2] REQUIREMENTS ANALYSIS                                           |
|      Converts high-level plan to specific requirements               |
|      Input: planner plan                                              |
|      Output: requirement spec (WHAT + constraints)                    |
|      v                                                                 |
|  [3] IMPLEMENTATION                                                   |
|      Executes based on requirements                                   |
|      Input: requirement spec, implementation guidelines              |
|      Output: code/docs/artifact                                       |
|      v                                                                 |
|  [4] REVIEW                                                          |
|      Verifies implementation against requirements                     |
|      Input: implementation output, requirement spec                  |
|      Output: pass / fail with specific issues                         |
|      v                                                                 |
|  [5] DOC REVIEW                                                       |
|      Verifies documentation is accurate and complete                  |
|      Input: modified/new files, related docs                         |
|      Output: doc pass / fail with missing items                       |
|      v                                                                 |
|  [6] EXPERIENCE CONSOLIDATION                                        |
|      Extracts learnings, updates rules/playbook                       |
|      Input: what worked, what failed, patterns observed              |
|      Output: updated repair_playbook.md, agent_learning_rules.md      |
|      v                                                                 |
|  [7] CONTROLLER COORDINATION                                         |
|      Orchestrates handoffs, checks exit criteria, decides next step  |
|      Input: all role outputs, PROJECT_CONTEXT.md                      |
|      Output: commit + push, loop back to Fix Phase, or phase done   |
|                                                                       |
+-----------------------------------------------------------------------+

    Loop back: Review/Doc fails -> Fix Phase -> back to [3] Implementation (max 3 retries)
    Phase done: All steps pass -> commit + push -> next phase
```

---

## Task Type Markers

**Every task in tasks.md MUST have a type marker**. This determines execution path.

| Marker | Meaning | Who Executes | Controller Role |
|--------|---------|--------------|-----------------|
| **[CODE]** | Code implementation, refactoring, or module changes | subagent (backend-engineer) | Orchestrate + review |
| **[DOC]** | Documentation-only: README, comments, non-code docs | Controller (self) | Execute directly |
| **[DATA]** | Data files: seed data, eval data, config changes | subagent or Controller | Orchestrate or execute |
| **[TEST]** | Adding/updating tests | subagent (backend-engineer) | Orchestrate + verify |
| **[AUTO]** | Automated verification or CI tasks | Controller (self) | Execute + report |

**Decision Rules**:
- Unmarked task = assume **[CODE]** (safer, always delegates)
- If unsure: use **[CODE]** and delegate
- **[DOC]** only if NO code changes required at all

---

## Trigger Conditions

Each role step has explicit trigger conditions. Controller checks these before dispatching.

### Step 1 - Planner
**Trigger**: Phase loaded from tasks.md, current state read from PROJECT_CONTEXT.md

### Step 2 - Requirements Analysis
**Trigger**: Step 1 plan exists and approved by Controller

### Step 3 - Implementation
**Trigger**: Step 2 requirements are unambiguous and complete

**Additional Trigger Check for [CODE] tasks**:
- MUST dispatch to subagent (never execute code directly)
- Verify subagent result file will be written

### Step 4 - Review
**Trigger**: Step 3 implementation output exists and tests pass locally

### Step 5 - Doc Review
**Trigger**: Step 4 review passed OR issues are fixable without design change

### Step 6 - Experience Consolidation
**Trigger**: Steps 1-5 completed (pass or fail), regardless of outcome

### Step 7 - Controller Coordination
**Trigger**: Step 6 complete

---

---

## Fix Phase (Code Review Failure Handling)

When Review [4] or Doc Review [5] fails, the Controller enters Fix Phase before looping back.

```
+-----------------------------------------------------------------------+
|                         FIX PHASE                                      |
+-----------------------------------------------------------------------+
|                                                                       |
|  [F1] ISSUE DOCUMENTATION                                            |
|      Record specific review findings with evidence                   |
|      Input: review output, line numbers, error patterns              |
|      v                                                                 |
|  [F2] ROOT CAUSE ANALYSIS                                            |
|      Determine WHY the issue occurred                                 |
|      Input: implementation output, requirements, review findings     |
|      v                                                                 |
|  [F3] SKILL CODIFICATION (if new pattern discovered)                 |
|      Check if this error is a new pattern                             |
|      Input: error_memory.jsonl, repair_playbook.md                   |
|      Output: new skill entry if pattern is novel                      |
|      v                                                                 |
|  [F4] FIX PLAN                                                        |
|      Create specific fix instructions for implementation             |
|      Input: root cause, review suggestions, Controller knowledge     |
|      Output: fix guidance document                                    |
|      v                                                                 |
|  [F5] RETRY DECISION                                                  |
|      Check retry count, decide next action                            |
|      Input: retry count (max 3), fix complexity                       |
|      Output: loop back to [3] / escalate to human                     |
|                                                                       |
+-----------------------------------------------------------------------+
```

### Fix Phase Rules

| Rule | Description |
|------|-------------|
| **Max Retries** | 3 total retries per phase |
| **Escalation Trigger** | After 3rd retry failure, escalate to human |
| **Fix Phase Entry** | Always enter Fix Phase before retry |
| **Skill Codification** | If new error pattern found, create skill entry |
| **Documentation** | All issues documented in review output |

### Fix Phase Entry Criteria

**Enter Fix Phase when**:
- Review [4] returns FAIL
- Doc Review [5] returns FAIL
- Any step returns unexpected errors

**Skip to direct retry when**:
- Typo fixes only
- Formatting changes (ruff fix)
- Documentation additions

### Escalation Format

When escalating after max retries:

```
## Escalation Report

**Phase**: [phase number and name]
**Task Type**: [CODE/DOC/DATA/TEST/AUTO]
**Total Retries**: 3

### What Was Tried

1. **Attempt 1**: [what was done]
2. **Attempt 2**: [what was done]
3. **Attempt 3**: [what was done]

### What Failed

- [Specific failure 1]
- [Specific failure 2]

### Root Cause Analysis

[Why the implementation keeps failing]

### Options Considered

1. [Option 1] - pros/cons
2. [Option 2] - pros/cons

### Recommendation

[Controller's recommended path forward]
```

## Role Responsibilities

### [1] Planner

**Purpose**: Create a clear, executable plan for the phase.

**Receives**:
- Phase goal from tasks.md with TYPE marker (e.g., Phase 15.4 **[CODE]**: Streamlit chat UI integration)
- Previous phase results (if any)
- Known constraints (from PROJECT_CONTEXT.md)

**Produces**:
- Step-by-step plan with numbered steps
- Each step has acceptance criteria
- Explicit dependencies between steps

**Exit Criteria**:
- Plan has no ambiguous steps
- Each step has concrete acceptance criteria
- Controller approves the plan

**Who performs**: Controller (self)
#### Skills Codification Process

When a pattern or error is discovered:

1. **Check for existing skill**: Search docs/harness/skills/ for similar patterns
2. **If new pattern**: Create new skill entry using TEMPLATE.md
3. **If known pattern**: Update existing skill with new learnings
4. **Update repair_playbook**: Add error -> fix mapping
5. **Log to error_memory**: Structured entry for future reference

```
+-----------------------------------------------------------------------+
|                    SKILLS CODIFICATION WORKFLOW                        |
+-----------------------------------------------------------------------+
|                                                                       |
|  [1] PATTERN DETECTION                                               |
|      An error or pattern is discovered during phase execution        |
|      v                                                                 |
|  [2] EXISTING SKILL CHECK                                            |
|      Search docs/harness/skills/ for matching pattern               |
|      v                                                                 |
|      +------------------------------------------------------------+   |
|      | Pattern is KNOWN    | Pattern is NEW                       |   |
|      +------------------------------------------------------------+   |
|      | Update skill with   | Create new skill entry               |   |
|      | new learnings      | using TEMPLATE.md                    |   |
|      +------------------------------------------------------------+   |
|      |                                                          v     |
|  [3] UPDATE REPAIR PLAYBOOK                                          |
|      Add error -> fix mapping                                        |
|      v                                                                 |
|  [4] LOG TO ERROR MEMORY                                            |
|      Structured JSONL entry                                          |
|      v                                                                 |
|  [5] INJECT INTO IMPLEMENTATION GUIDANCE                             |
|      Reference skill in Fix Phase dispatch                           |
|                                                                       |
+-----------------------------------------------------------------------+
```

#### Skill Entry Requirements

| Field | Required | Description |
|-------|----------|-------------|
| Skill ID | Yes | `skill_{domain}_{short_name}` format |
| Version | Yes | Semantic versioning |
| Pattern Type | Yes | error_fix / best_practice / anti_pattern |
| Problem Statement | Yes | Clear description of the issue |
| Solution Steps | Yes | Numbered action items |
| Code Examples | Conditional | Before/after for code patterns |
| Validation | Yes | How to verify the fix |
| Related Skills | No | Links to related skill entries |
 or project-director subagent for complex phases.

**Critical Check**: If task is **[CODE]**, plan must include delegation to subagent, not Controller self-implementation.

---

### [2] Requirements Analysis

**Purpose**: Convert high-level plan into concrete requirements.

**Receives**:
- Planner step-by-step plan with TYPE markers
- Domain knowledge (from docs/technical/, ARCHITECTURE.md)
- Existing OpenSpec specs

**Produces**:
- Requirement spec with:
  - Functional requirements (WHAT the system must do)
  - Non-functional constraints (performance, compatibility, boundaries)
  - Acceptance test criteria (how to verify)
- Input for the executing agent

**Exit Criteria**:
- Requirements are unambiguous
- Every plan step has corresponding requirements
- No assumptions left unspoken

**Who performs**: Dedicated subagent (general-purpose with requirements-analyst role) or Controller for simple phases.

#### Requirements Analysis Template (Product Manager Spec)

Requirements must be detailed enough to code from without asking questions.

```
## Requirements Specification: {Phase Name}

### Phase Information
- **Phase ID**: {phase_number}
- **Task Type**: [CODE/DOC/DATA/TEST/AUTO]
- **Priority**: Critical / High / Medium / Low
- **OpenSpec Reference**: {if applicable}

---

### Functional Requirements

#### FR-{number}: {Requirement Title}

| Field | Value |
|-------|-------|
| **ID** | FR-{number} |
| **Title** | {Short descriptive title} |
| **Type** | `feature` / `bug_fix` / `refactor` / `enhancement` |
| **Module** | {affected module(s)} |

**Description**:
{Detailed description of what this requirement does. Be specific about behavior.}

**Fields** (for data/API requirements):

| Field Name | Type | Required | Description | Valid Values / Constraints |
|------------|------|----------|-------------|-----------------------------|
| {field_name} | {string/int/boolean/object/array} | Yes/No | {description} | {constraints} |

**API Signature** (if applicable):
\`\`\`python
{function_signature}
# or
{endpoint}: {method}
\`\`\`

**Data Structure** (if applicable):
\`\`\`python
class {ClassName}:
    """Description of the data structure."""
    
    {field_name}: {type}
    """Description of this field."""
    
    def {method_name}(self, {params}) -> {return_type}:
        """Description of this method."""
\`\`\`

**Acceptance Criteria**:
- [ ] {Specific check 1}
- [ ] {Specific check 2}
- [ ] {Specific check 3}

**Test Strategy**:
| Test Type | Scope | Method |
|-----------|-------|--------|
| Unit | {module} | {test file} |
| Integration | {flow} | {test file} |

**Related Requirements**:
- {other FR IDs that relate}

**Edge Cases**:
- {edge case 1} -> expected behavior
- {edge case 2} -> expected behavior

---

### Non-Functional Requirements

#### NFR-{number}: {Title}

| Field | Value |
|-------|-------|
| **Type** | `performance` / `security` / `compatibility` / `maintainability` / `reliability` |

**Requirement**: {specific constraint}

**Measurement**: {how to verify}

---

### Constraints

| Constraint | Description | Source |
|------------|-------------|--------|
| {constraint_id} | {description} | {OpenSpec / legacy / implicit} |

---

### Out of Scope

- {item 1}
- {item 2}

---

### Dependencies

| Dependency | Type | Required For | Notes |
|------------|------|--------------|-------|
| {module} | `import` / `runtime` / `build` | {FR ID} | {notes} |

---

### Verification Plan

| FR ID | Verification Method | Expected Result |
|-------|---------------------|------------------|
| FR-1 | {test/check} | {expected outcome} |

---

### Open Questions

| Question | Impact | Resolution Plan |
|----------|--------|-----------------|
| {question} | {High/Medium/Low} | {plan to resolve} |

---

### Change Log

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | YYYY-MM-DD | Initial requirements |
\`\`\`



---

### [3] Implementation

**Purpose**: Execute based on requirements.

**Receives**:
- Requirement spec with TYPE marker
- Implementation guidelines (from AGENTS.md, repair_playbook.md)
- Tech stack constraints

**Produces**:
- Working implementation (code, docs, or artifacts)
- Unit tests for the implemented module
- Subagent result file: subagent_results/{task_id}_result.md

**Exit Criteria**:
- Implementation meets all functional requirements
- Unit tests pass for the modified module
- No ruff errors

**Who performs**: Specialized subagent based on TYPE:

| Task Type | Subagent | Verification |
|-----------|----------|--------------|
| [CODE] | backend-engineer | code-reviewer |
| [DATA] | backend-engineer | tests |
| [TEST] | backend-engineer | Controller verifies |
| [DOC] | Controller (self) | doc-reviewer |

**CRITICAL RULE - Lesson 1 Fix**:

    +------------------------------------------------------------------+
    |  CONTROLLER NEVER IMPLEMENTS CODE DIRECTLY                        |
    |  For [CODE] tasks: ALWAYS dispatch to backend-engineer subagent   |
    |  Controller role = Orchestrate + Review + Approve                |
    |  Controller NEVER = Implement + Write code                        |
    +------------------------------------------------------------------+

---

### [4] Review

**Purpose**: Verify implementation against requirements.

**Receives**:
- Implementation output (from subagent result file)
- Requirement spec (from step 2)
- Acceptance test criteria

**Produces**:
- Review result: PASS / FAIL
- If FAIL: specific issues with line numbers
- Suggested fixes

**Exit Criteria**:
- All requirements satisfied
- No missing functionality
- No regression introduced

**Who performs**: code-reviewer subagent

**Repeat Mechanism**:
- If FAIL: enter Fix Phase
- Max 3 retries per phase
- If still failing after 3 retries: escalate to human with escalation report

---

### [5] Doc Review

**Purpose**: Verify documentation accuracy.

**Receives**:
- Modified/new files
- Related existing documentation
- Doc requirements (from this phase)

**Produces**:
- Doc review result: PASS / FAIL
- If FAIL: list of missing or incorrect docs
- Boundary wording check (portfolio-facing docs)

**Exit Criteria**:
- All modified/new files have corresponding docs
- Boundary wording present in portfolio docs
- No misleading claims

**Who performs**: Controller (self)
#### Skills Codification Process

When a pattern or error is discovered:

1. **Check for existing skill**: Search docs/harness/skills/ for similar patterns
2. **If new pattern**: Create new skill entry using TEMPLATE.md
3. **If known pattern**: Update existing skill with new learnings
4. **Update repair_playbook**: Add error -> fix mapping
5. **Log to error_memory**: Structured entry for future reference

```
+-----------------------------------------------------------------------+
|                    SKILLS CODIFICATION WORKFLOW                        |
+-----------------------------------------------------------------------+
|                                                                       |
|  [1] PATTERN DETECTION                                               |
|      An error or pattern is discovered during phase execution        |
|      v                                                                 |
|  [2] EXISTING SKILL CHECK                                            |
|      Search docs/harness/skills/ for matching pattern               |
|      v                                                                 |
|      +------------------------------------------------------------+   |
|      | Pattern is KNOWN    | Pattern is NEW                       |   |
|      +------------------------------------------------------------+   |
|      | Update skill with   | Create new skill entry               |   |
|      | new learnings      | using TEMPLATE.md                    |   |
|      +------------------------------------------------------------+   |
|      |                                                          v     |
|  [3] UPDATE REPAIR PLAYBOOK                                          |
|      Add error -> fix mapping                                        |
|      v                                                                 |
|  [4] LOG TO ERROR MEMORY                                            |
|      Structured JSONL entry                                          |
|      v                                                                 |
|  [5] INJECT INTO IMPLEMENTATION GUIDANCE                             |
|      Reference skill in Fix Phase dispatch                           |
|                                                                       |
+-----------------------------------------------------------------------+
```

#### Skill Entry Requirements

| Field | Required | Description |
|-------|----------|-------------|
| Skill ID | Yes | `skill_{domain}_{short_name}` format |
| Version | Yes | Semantic versioning |
| Pattern Type | Yes | error_fix / best_practice / anti_pattern |
| Problem Statement | Yes | Clear description of the issue |
| Solution Steps | Yes | Numbered action items |
| Code Examples | Conditional | Before/after for code patterns |
| Validation | Yes | How to verify the fix |
| Related Skills | No | Links to related skill entries |
 for simple docs, doc-reviewer subagent for complex docs

**Key Check** (per AGENTS.md Section 13):
- Fake embeddings: Pipeline verification only -- no semantic retrieval quality
- Seed data: All knowledge and eval data are synthetic
- No auto-send: TicketPilot never sends customer replies automatically
- Human review: High-risk outputs require human review
- Evaluation: Offline evaluation on 101 synthetic tickets

---

### [6] Experience Consolidation

**Purpose**: Extract learnings to improve future phases, codify patterns into reusable skills.

**Receives**:
- Phase execution log (what happened at each step)
- Any errors or blockers encountered
- What worked well
- What could be improved

**Produces**:
- Updates to repair_playbook.md (if new error pattern found)
- Updates to agent_learning_rules.md (if new stable rule found)
- Entries to error_memory.jsonl (if errors encountered)
- **Skill entries** (if new patterns discovered) in docs/harness/skills/
- Lessons for next phase handoff

**Exit Criteria**:
- All new patterns documented
- No undocumented error left untracked
- New skills created for novel patterns

**Who performs**: Controller (self)
#### Skills Codification Process

When a pattern or error is discovered:

1. **Check for existing skill**: Search docs/harness/skills/ for similar patterns
2. **If new pattern**: Create new skill entry using TEMPLATE.md
3. **If known pattern**: Update existing skill with new learnings
4. **Update repair_playbook**: Add error -> fix mapping
5. **Log to error_memory**: Structured entry for future reference

```
+-----------------------------------------------------------------------+
|                    SKILLS CODIFICATION WORKFLOW                        |
+-----------------------------------------------------------------------+
|                                                                       |
|  [1] PATTERN DETECTION                                               |
|      An error or pattern is discovered during phase execution        |
|      v                                                                 |
|  [2] EXISTING SKILL CHECK                                            |
|      Search docs/harness/skills/ for matching pattern               |
|      v                                                                 |
|      +------------------------------------------------------------+   |
|      | Pattern is KNOWN    | Pattern is NEW                       |   |
|      +------------------------------------------------------------+   |
|      | Update skill with   | Create new skill entry               |   |
|      | new learnings      | using TEMPLATE.md                    |   |
|      +------------------------------------------------------------+   |
|      |                                                          v     |
|  [3] UPDATE REPAIR PLAYBOOK                                          |
|      Add error -> fix mapping                                        |
|      v                                                                 |
|  [4] LOG TO ERROR MEMORY                                            |
|      Structured JSONL entry                                          |
|      v                                                                 |
|  [5] INJECT INTO IMPLEMENTATION GUIDANCE                             |
|      Reference skill in Fix Phase dispatch                           |
|                                                                       |
+-----------------------------------------------------------------------+
```

#### Skill Entry Requirements

| Field | Required | Description |
|-------|----------|-------------|
| Skill ID | Yes | `skill_{domain}_{short_name}` format |
| Version | Yes | Semantic versioning |
| Pattern Type | Yes | error_fix / best_practice / anti_pattern |
| Problem Statement | Yes | Clear description of the issue |
| Solution Steps | Yes | Numbered action items |
| Code Examples | Conditional | Before/after for code patterns |
| Validation | Yes | How to verify the fix |
| Related Skills | No | Links to related skill entries |


---

### [7] Controller Coordination

**Purpose**: Orchestrate the loop, decide next action.

**Duties**:

1. **Handoff Management**
   - Ensure each role receives correct input from previous role
   - Verify handoff protocol followed (see below)
   - Track role outputs for audit trail

2. **Exit Criteria Checking**
   - Each role must pass before moving to next
   - Document failures with specific evidence

3. **Loop Control**
   - If Review [4] fails: enter Fix Phase
   - If Doc Review [5] fails: enter Fix Phase
   - Max 3 retries per phase
   - After 3 retries: escalate to human

4. **Decision Authority** (per AGENTS.md Section 11)
   - Controller acts autonomously on execution decisions
   - Controller asks human only when: genuinely blocked, non-negotiable rule is at risk, A-class change, deletion risk

5. **Context Management** (per AGENTS.md Section 12)
   - Update PROJECT_CONTEXT.md after phase completion
   - Commit after successful subagent + passing tests
   - Never commit with failing tests
   - Store structured handoff summaries (not raw logs)

6. **Compression Handling** (per AGENTS.md Section 15)
   - **Lesson 2 Fix**: On compression, FIRST check subagent status
   - If subagent completed: write output, then compress
   - If subagent in-flight: wait or commit partial state first
   - NEVER compress mid-subagent-work (results will be lost)
   - Write compression_handoff.md with subagent status clearly marked

**Exit Criteria**:
- Phase fully complete: commit + push
- OR: Fix Phase entered (with retry counter incremented)
- OR: Escalation documented with options

---

## Handoff Protocol

Each role transition follows this protocol:

    +-----------------------------------------------------------------------+
    |                         HANDOFF PROTOCOL                              |
    +-----------------------------------------------------------------------+
    |                                                                       |
    |  BEFORE HANDOFF (current role):                                      |
    |  1. Verify exit criteria met (all checks green)                      |
    |  2. Write structured output to designated file                       |
    |  3. Update tasks.md status (if applicable)                          |
    |  4. Notify Controller of completion                                  |
    |                                                                       |
    |  HANDOFF SIGNAL (Controller):                                        |
    |  1. Read previous role output file                                   |
    |  2. Validate output completeness                                     |
    |  3. Dispatch next role with explicit input reference                |
    |  4. Set clear scope and acceptance criteria for next role            |
    |                                                                       |
    |  AFTER HANDOFF (next role):                                          |
    |  1. Read handoff input file(s)                                       |
    |  2. Acknowledge scope                                                 |
    |  3. Execute and produce output                                       |
    |  4. Write output to designated file                                  |
    |  5. Notify Controller of completion                                  |
    |                                                                       |
    +-----------------------------------------------------------------------+

### Handoff Output Locations

| From Role                 | To Role         | Output Location                              | File Format |
|---------------------------|-----------------|----------------------------------------------|-------------|
| Planner                   | Req Analysis    | subagent_results/{phase}_plan.md             | Markdown    |
| Requirements Analysis     | Implementation  | subagent_results/{phase}_requirements.md     | Markdown    |
| Implementation            | Review          | subagent_results/{task_id}_result.md         | Markdown    |
| Review                    | Controller      | subagent_results/{task_id}_review.md         | Markdown    |
| Doc Review                | Controller      | subagent_results/{task_id}_doc_review.md     | Markdown    |
| Experience Consolidation  | Controller      | reports/harness/error_memory.jsonl          | JSONL       |
| Fix Phase                 | Implementation  | subagent_results/{phase}_fix_guidance.md    | Markdown    |

### Handoff Content Requirements

Each handoff output MUST contain:
- **Phase ID**: Which phase this is for
- **Task TYPE**: [CODE] / [DOC] / [DATA] / [TEST] / [AUTO]
- **Role**: Who produced this output
- **Timestamp**: When produced
- **Summary**: What was done in 1-2 sentences
- **Details**: Specific findings, decisions, or outputs
- **Next Action**: What should happen next
- **Blockers**: Any issues that need resolution

---

## Controller Coordination Checklist

Use this checklist for each phase loop cycle:

    CONTROLLER COORDINATION CHECKLIST
    =================================

    PHASE: [phase number and name]
    TASK TYPE: [CODE/DOC/DATA/TEST/AUTO]
    LOOP COUNT: [1/2/3]

    [ ] Read PROJECT_CONTEXT.md for current state
    [ ] Read tasks.md for phase requirements
    [ ] Confirm active OpenSpec change
    [ ] Note task type - determines delegation strategy

    STEP 1 - PLANNER
    [ ] Planner created/modified plan
    [ ] Plan has numbered steps with acceptance criteria
    [ ] Plan approved by Controller
    [ ] For [CODE]: plan delegates to subagent, not Controller

    STEP 2 - REQUIREMENTS ANALYSIS
    [ ] Requirements spec produced using Product Manager template
    [ ] All plan steps have corresponding requirements
    [ ] No ambiguous requirements
    [ ] Field definitions included for data/API requirements
    [ ] API signatures specified (if applicable)
    [ ] Acceptance criteria are actionable

    STEP 3 - IMPLEMENTATION
    [TYPE CHECK]
    [CODE]: [ ] Dispatched to backend-engineer subagent
    [CODE]: [ ] Controller did NOT implement code directly
    [DOC]:  [ ] Executed by Controller (doc-only, no code changes)
    [DATA]: [ ] Executed appropriately
    [ ] Implementation complete
    [ ] Unit tests for modified module pass
    [ ] Ruff clean
    [ ] Subagent result written to designated file

    STEP 4 - REVIEW
    [ ] Review subagent dispatched
    [ ] Review result: PASS / FAIL
    [ ] If FAIL: enter Fix Phase
    [ ] If PASS: proceed to step 5

    STEP 5 - DOC REVIEW
    [ ] Doc review completed
    [ ] Boundary wording verified in portfolio docs
    [ ] Doc result: PASS / FAIL
    [ ] If FAIL: enter Fix Phase

    STEP 6 - EXPERIENCE CONSOLIDATION
    [ ] Error patterns documented (if any)
    [ ] repair_playbook.md updated (if new patterns)
    [ ] agent_learning_rules.md updated (if new rules)
    [ ] Skills codified (if new patterns discovered)
    [ ] Compression handoff status verified (if context was compressed)

    STEP 7 - CONTROLLER COORDINATION
    [ ] All exit criteria met
    [ ] tasks.md updated with phase status
    [ ] PROJECT_CONTEXT.md updated
    [ ] Decision made: commit+push / Fix Phase / escalate

    FIX PHASE (if entered):
    [ ] F1: Issue documented with evidence
    [ ] F2: Root cause identified
    [ ] F3: Skill codification checked
    [ ] F4: Fix plan created
    [ ] F5: Retry decision made (loop back / escalate)

    COMMIT DECISION:
    [ ] Commit and push
    [ ] Loop back to step [3/4/5], retry [1/2/3]
    [ ] Escalate to human (blocker: [description])

---

## Repeat/Check Mechanism

### AI Repeated Checks

After Implementation [3] completes, Controller triggers:

1. **Automated checks** (run by Controller):
   - uv run ruff check .
   - uv run pytest tests/unit/test_{module}.py -v --tb=short
   - grep for overclaiming in modified files

2. **Review [4]** triggers deeper check:
   - code-reviewer reads implementation
   - code-reviewer verifies against requirements
   - code-reviewer checks for edge cases

3. **Doc Review [5]** triggers boundary check:
   - Check portfolio docs for boundary wording
   - Verify no overclaiming (production-ready, real-world, etc.)
   - Check all new/modified docs are linked

### Retry Logic

| Step               | Max Retries | On Failure                                                     |
|--------------------|-------------|----------------------------------------------------------------|
| Implementation [3]  | 3           | Enter Fix Phase, then back to [3]                               |
| Review [4]         | 3           | Enter Fix Phase if impl issue, escalate if requirements issue    |
| Doc Review [5]     | 3           | Enter Fix Phase if content issue                                |
| Fix Phase          | N/A         | Always enters before retry, not counted separately              |

After max retries:
- Document what was tried
- List specific failures
- Escalate to human with options

---

## Lessons Learned (Encoded in Workflow)

### Lesson 1: Controller kept implementing code directly
**Problem**: Controller violated subagent principle, did B2 task directly
**Rule**: All roles (Planner, Req Analysis, Implementation, Review, Doc Review, Experience) must be subagents for [CODE] tasks. Controller only orchestrates.

### Lesson 2: Context compression lost rules
**Problem**: Compression happened mid-work, AGENTS.md rules were not followed on resume
**Rule**: On compression, check subagent status FIRST. Write compression_handoff.md with explicit subagent status: completed / in-flight (committed) / in-flight (not committed).

### Lesson 3: tasks.md had no task-type marking
**Problem**: Could not tell from A2 "update ARCHITECTURE.md" that it was doc-only vs A1 "fix RetrievalTrace" that it was code
**Rule**: All tasks MUST have [CODE]/[DOC]/[DATA]/[TEST]/[AUTO] marker. Unmarked = assume [CODE] (delegate).

### Lesson 4: Missing trigger conditions
**Problem**: Rules existed but did not explicitly say WHEN to trigger
**Rule**: Each step has explicit "Trigger" section. Controller checks trigger conditions before dispatching.

### Lesson 5: Contradictions in rules
**Problem**: Section 9 vs 11 contradiction in AGENTS.md about code implementation
**Rule**: Unified - Controller NEVER implements code. Always delegate to subagent for [CODE] tasks.

### Lesson 6: Skills not codified
**Problem**: Error patterns were documented but not made reusable
**Rule**: New patterns -> skill entries in docs/harness/skills/ using TEMPLATE.md

### Lesson 7: Fix Phase workflow missing
**Problem**: Review failures led directly to retry without systematic analysis
**Rule**: Always enter Fix Phase before retry. Document issue, analyze root cause, codify skill, create fix plan.

---

## Integration with AGENTS.md

This document extends these sections:

### Section 11: Controller Autonomy Rules

PHASE_LOOP operationalizes "Act First, Ask Only When Blocked":
- Steps 1-6 are autonomous execution (no human interruption)
- Step 7 is the decision point (commit / retry / escalate)
- Escalation triggers documented in step 7 match Section 11 escalation triggers
- **Subagent Principle** (Section 11): All [CODE] tasks delegated to backend-engineer

### Section 12: Controller Context Rules

PHASE_LOOP enforces:
- PROJECT_CONTEXT.md updated at step 7
- Commit trigger: "subagent returns success + module tests green"
- Structured handoff summaries (handoff protocol above)
- Subagent results go to subagent_results/
- Error memory maintained at step 6

### Section 15: Context Compression Handoff Rules

PHASE_LOOP adds explicit trigger check:
- Step 7 includes compression detection
- If compress during loop: write compression_handoff.md
- **Check subagent status before compression**
- Resume from handoff file on resume
- Subagent status MUST be explicitly recorded

### Not Duplicated (kept in AGENTS.md)

- Non-negotiable boundaries (Section 2)
- Quality gate rules (Section 8)
- OpenSpec workflow (Section 7)
- Error memory format (Section 14)
- Portfolio boundary wording (Section 13)

---

## File Locations Reference

| Purpose                    | Location                                      |
|----------------------------|-----------------------------------------------|
| Phase plan output          | subagent_results/{phase}_plan.md              |
| Requirements spec          | subagent_results/{phase}_requirements.md      |
| Implementation result      | subagent_results/{task_id}_result.md          |
| Review result              | subagent_results/{task_id}_review.md          |
| Doc review result          | subagent_results/{task_id}_doc_review.md      |
| Error memory               | reports/harness/error_memory.jsonl            |
| Repair playbook            | reports/harness/repair_playbook.md             |
| Agent learning rules       | docs/harness/agent_learning_rules.md          |
| Skills directory           | docs/harness/skills/                          |
| Skills template            | docs/harness/skills/TEMPLATE.md              |
| Project context            | docs/harness/PROJECT_CONTEXT.md               |
| Compression handoff        | reports/harness/compression_handoff_{ts}.md    |
| Controller coordination     | docs/harness/CONTROLLER_HARNESS_PRACTICE.md    |

---

## Example: Phase Execution

Phase 15.4 **[CODE]**: Fix RetrievalTrace class collision

**STEP 1 - PLANNER** (Controller)
- Task type: [CODE] (requires delegation)
- Output: subagent_results/phase15.4_plan.md
- Steps: Identify conflict, choose strategy, implement rename, update refs, run tests
- Acceptance: No class name collision, all tests pass

**STEP 2 - REQUIREMENTS ANALYSIS** (subagent)
- Input: subagent_results/phase15.4_plan.md
- Output: subagent_results/phase15.4_requirements.md
- FR1: RetrievalTrace in traces.py must not shadow schema/retrieval.py
- FR2: All imports must be updated
- FR3: Tests must still pass

**STEP 3 - IMPLEMENTATION** (backend-engineer subagent) - **NOT Controller**
- Input: subagent_results/phase15.4_requirements.md
- Output: subagent_results/retrievaltrace_fix_result.md + code changes
- **Controller did NOT write code** - delegated to subagent

**STEP 4 - REVIEW** (code-reviewer subagent)
- Input: implementation output + requirements
- Output: subagent_results/retrievaltrace_fix_review.md
- Result: PASS

**STEP 5 - DOC REVIEW** (Controller)
- Input: modified files
- Output: subagent_results/retrievaltrace_fix_doc_review.md
- Result: PASS (no new docs needed)

**STEP 6 - EXPERIENCE CONSOLIDATION** (Controller)
- Check error_memory.jsonl for similar issues
- Document: class collision detection pattern
- Update repair_playbook.md if new pattern

**STEP 7 - CONTROLLER COORDINATION**
- Update tasks.md: Phase 15.4 complete
- Update PROJECT_CONTEXT.md
- Commit and push


## Example: Phase with Fix Phase

Phase 15.5 **[CODE]**: Add pagination to ticket retrieval

**STEPS 1-3**: Completed as normal

**STEP 4 - REVIEW** (code-reviewer subagent)
- Input: implementation output + requirements
- Output: subagent_results/phase15.5_review.md
- Result: **FAIL**
- Issues:
  - Line 45: Missing offset parameter handling
  - Line 67: Page size validation missing

**FIX PHASE ENTERED** (retry count: 1)

**F1 - Issue Documentation**
- Documented line 45 and 67 issues with code snippets

**F2 - Root Cause Analysis**
- Offset parameter not included in API signature
- Validation logic missing in service layer

**F3 - Skill Codification**
- Searched docs/harness/skills/ for pagination patterns
- Found skill_retrieval_pagination_offset - updated with new learning
- If new pattern: create new skill entry

**F4 - Fix Plan**
- Add offset parameter to API signature
- Add page_size validation (1-100 range)
- Update unit tests

**F5 - Retry Decision**
- Retry count 1 < 3: loop back to [3]

**STEPS 3-5 RETRIED** with fixes applied

**STEP 4 - REVIEW** (second attempt)
- Result: **PASS**

**STEPS 5-7 COMPLETED**

---
## Summary

| Concept          | Definition                                                                 |
|------------------|----------------------------------------------------------------------------|
| Phase            | One logical unit of work from tasks.md                                     |
| Loop             | 7 steps executed in sequence per phase                                     |
| Controller       | Orchestrates loop, delegates execution, NEVER implements code              |
| Task Type        | [CODE]/[DOC]/[DATA]/[TEST]/[AUTO] - determines execution path             |
| Trigger          | Explicit conditions checked before each step dispatch                      |
| Roles            | Planner, Requirements Analysis, Implementation, Review, Doc Review, Experience Consolidation |
| Handoff          | Structured output passed between roles                                    |
| Exit criteria    | Conditions that must be met before moving to next role                     |
| Fix Phase        | Systematic failure analysis before retry (5 sub-steps)                    |
| Skills Codification | Extract learnings into reusable skill entries                          |
| Repeat mechanism | Max 3 retries per phase, Fix Phase entered before each retry |
| Compression      | System-triggered context save - check subagent status FIRST                |

This design minimizes human involvement while ensuring quality through automated checks, systematic fix workflows, and reusable skill codification.
