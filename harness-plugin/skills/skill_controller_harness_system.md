---
phase: master-system
change: controller-harness-system
last_updated: 2026-05-08
owner: controller
---

# Skill: Controller Harness System (Master Skill)

## Metadata

| Field | Value |
|-------|-------|
| **Skill ID** | skill_controller_harness_system |
| **Version** | 1.0.0 |
| **Created** | 2026-05-08 |
| **Last Updated** | 2026-05-08 |
| **Author** | Controller (auto-generated) |
| **Status** | active |
| **Type** | Master Skill (points to other skills) |

## Classification

| Field | Value |
|-------|-------|
| **Domain** | workflow |
| **Pattern Type** | best_practice |
| **Complexity** | complex (system-level) |



# System Architecture Diagram

```
+=========================================================================+
|                    CONTROLLER HARNESS SYSTEM                            |
+=========================================================================+
|                                                                          |
|  +------------------+     +------------------+     +------------------+  |
|  |   MAIN CONTEXT   |     |  OPENSPEC STATE  |     |   SHARED INFO    |  |
|  |   (Claude Code)  |<--->|   (Anchor Only)  |<--->|   (FILES)        |  |
|  +------------------+     +------------------+     +------------------+  |
|          |                         |                        |          |
|          v                         v                        v          |
|  +---------------------------------------------------------------------+ |
|  |                     PHASE LOOP (7 Steps)                           | |
|  +---------------------------------------------------------------------+ |
|  |                                                                     | |
|  |  [1] PLANNER ------> [2] REQ ANALYSIS ------> [3] IMPLEMENTATION  | |
|  |       |                     |                     |                | |
|  |       | project-director    | general-purpose     | backend-       | |
|  |       | subagent            | subagent             | engineer       | |
|  |       |                     |                     | subagent       | |
|  |       v                     v                     v                | |
|  |  [4] REVIEW -------> [5] DOC REVIEW -------> [6] EXPERIENCE       | |
|  |       |                     |                     |                | |
|  |       | code-reviewer       | code-reviewer       | general-       | |
|  |       | subagent            | subagent            | purpose        | |
|  |       |                     |                     | subagent       | |
|  |       v                     v                     v                | |
|  |  +--------------------------------------------------------------+  | |
|  |  | [7] CONTROLLER COORDINATION                                  |  | |
|  |  | - Check exit criteria                                       |  | |
|  |  | - Fix Phase or commit+push                                  |  | |
|  |  +--------------------------------------------------------------+  | |
|  |                                                                     | |
|  +---------------------------------------------------------------------+ |
|          |                         |                        |          |
|          v                         v                        v          |
|  +------------------+     +------------------+     +------------------+  |
|  | SUBAGENT RESULTS  |     | ERROR MEMORY     |     | REPAIR PLAYBOOK |  |
|  | (phase_X_Y.md)    |     | (error_memory    |     | (harness)       |  |
|  |                   |     |  .jsonl)         |     |                 |  |
|  +------------------+     +------------------+     +------------------+  |
|                                                                          |
+=========================================================================+

                          FAILURE PATH (Fix Phase)
                          ========================

     Review/Doc Fail
          |
          v
     +---------+
     | FIX     |
     | PHASE   | -----> F1: Issue Documentation
     | (F1-F5) | -----> F2: Root Cause Analysis
     +---------+ -----> F3: Skill Codification
          |         -----> F4: Fix Plan
          |         -----> F5: Retry Decision
          |                    |
          +-----> max 3 retries -----> ESCALATE
          |
          +-----> pass -----> Continue to [7]

```

# File Structure

ticketpilot/
docs/harness/                              # Controller harness docs
  CONTROLLER_HARNESS_PRACTICE.md         # Core principles (English)
  PROJECT_CONTEXT.md                     # Current state tracking
  PHASE_LOOP.md                          # 7-step workflow definition
  skills/                                # Reusable skill entries
    TEMPLATE.md                        # Skill template
    skill_workflow_phase_loop.md       # Phase loop details
    skill_workflow_subagent_delegation.md  # Delegation rules
    skill_requirements_pm_style.md      # PM-style requirements
    skill_chat_review_decision_display.md
    skill_chat_action_badge_colors.md
    skill_chat_streamlit_multipage_handoff.md
    skill_controller_harness_system.md  # THIS FILE (master)
  AGENTS.md                              # Core agent rules/constraints

subagent_results/                          # Phase execution artifacts
  phase15.4_plan.md
  phase15.4_requirements.md
  phase15.4_implementation.md
  phase15.4_review.md
  phase15.4_doc_review.md
  phase15.4_experience.md

reports/harness/                            # Error memory & playbooks
  error_memory.jsonl                     # Real-time error logging
  repair_playbook.md                      # Categorized repair procedures
  compression_handoff.md                   # Context compression handling
  architecture_decision_log.md
  validation_log.md

openspec/                                   # OpenSpec state anchor
  changes/
    {active-change}/
      tasks.md                       # Task tracking
      design.md                      # Architecture decisions
      repair_entry.md                # Error tracking per change
  specs/

AGENTS.md                                  # Core rules and constraints

# Subagent Role Mapping

| Phase Step | Subagent Type | When to Use |
|------------|--------------|-------------|
| **1 - PLANNER** | project-director | Create step-by-step plans with acceptance criteria |
| **2 - REQUIREMENTS ANALYSIS** | general-purpose | Convert plans to detailed requirements with field definitions |
| **3 - IMPLEMENTATION** | backend-engineer | Write code, refactor, module changes ([CODE] tasks) |
| **4 - REVIEW** | code-reviewer | Verify implementation against requirements |
| **5 - DOC REVIEW** | code-reviewer | Verify documentation accuracy and completeness |
| **6 - EXPERIENCE CONSOLIDATION** | general-purpose | Extract learnings, codify patterns |
| **Fix Phase** | system-architect | Workflow design, escalation handling |

### Delegation Rules

| Task Type | Who Executes | Controller Role |
|-----------|--------------|-----------------|
| [CODE] | backend-engineer subagent | Orchestrate + review (NEVER self) |
| [DOC] | Controller (self) | Execute directly |
| [DATA/TEST] | Dispatch appropriately | Orchestrate or execute |

### Output File Naming Convention

subagent_results/{phase}_{step}.md

Examples:
  phase15.4_plan.md           (Step 1: Planner)
  phase15.4_requirements.md    (Step 2: Requirements)
  phase15.4_implementation.md  (Step 3: Implementation)
  phase15.4_review.md          (Step 4: Review)
  phase15.4_doc_review.md      (Step 5: Doc Review)
  phase15.4_experience.md      (Step 6: Experience)

Handoff Protocol:
  1. Before: Check subagent status
  2. During: Monitor for context compression
  3. After: Read result file, verify completeness

# 7-Step Phase Loop Process Flow

| Step | Name | Role | Subagent | Input | Output | Exit Criteria |
|------|------|------|----------|-------|--------|---------------|
| 1 | PLANNER | Create/modify plan | project-director | Phase goal from tasks.md | Step-by-step plan with acceptance criteria | Plan approved by Controller |
| 2 | REQUIREMENTS ANALYSIS | Convert to concrete requirements | general-purpose | Planner plan | Requirements spec with field definitions | No ambiguous items |
| 3 | IMPLEMENTATION | Execute based on requirements | backend-engineer | Requirements spec | Code/docs/artifact | Meets all acceptance criteria |
| 4 | REVIEW | Verify implementation | code-reviewer | Implementation + requirements | Pass/fail with specific issues | PASS required |
| 5 | DOC REVIEW | Verify documentation | code-reviewer | Modified files + related docs | Doc pass/fail with missing items | PASS required |
| 6 | EXPERIENCE CONSOLIDATION | Extract learnings | general-purpose | All step outputs | Updated rules/playbook | Lessons codified |
| 7 | CONTROLLER COORDINATION | Orchestrate handoffs | Controller | All outputs | Commit+push OR Fix Phase OR next phase | Decision made |

### Fix Phase (on Review/Doc Failure)

When Step 4 or 5 fails:

| Sub-step | Action | Output |
|----------|--------|--------|
| F1 | Issue Documentation | Record findings with evidence |
| F2 | Root Cause Analysis | Determine WHY failure occurred |
| F3 | Skill Codification | Create/update skill if new pattern |
| F4 | Fix Plan | Create specific fix guidance |
| F5 | Retry Decision | Loop back (max 3) or escalate |

**Max Retries**: 3 total per phase
**Escalation Trigger**: After 3rd retry failure

# Shared Information Locations

| File | Purpose | Update Frequency | TTL |
|------|---------|------------------|-----|
| docs/harness/PROJECT_CONTEXT.md | Current phase, tasks, next actions | Every phase transition | 7 days |
| docs/harness/PHASE_LOOP.md | 7-step workflow definition | When process changes | Permanent |
| reports/harness/error_memory.jsonl | Real-time error logging | On every error | Review weekly |
| reports/harness/repair_playbook.md | Categorized repair procedures | On new error patterns | Permanent |
| reports/harness/compression_handoff.md | Context compression handling | When compression occurs | Permanent |
| docs/harness/skills/*.md | Reusable skill entries | On new patterns | Permanent |
| subagent_results/*.md | Phase execution artifacts | Every phase step | Delete after phase done |
| openspec/changes/{active}/tasks.md | Task tracking | Every task state change | Until phase complete |

# Quick Start Checklist

## Session Start
- [ ] Read openspec/changes/{active}/tasks.md - confirm current task state
- [ ] Read docs/harness/PROJECT_CONTEXT.md - understand current phase
- [ ] Check reports/harness/error_memory.jsonl - any P1 errors?
- [ ] Review docs/harness/AGENTS.md if needed - core constraints

## Phase Execution
- [ ] Identify phase from tasks.md
- [ ] Execute Step 1 (Planner) -> output: subagent_results/{phase}_plan.md
- [ ] Execute Step 2 (Requirements) -> output: subagent_results/{phase}_requirements.md
- [ ] Execute Step 3 (Implementation) -> output: subagent_results/{phase}_implementation.md
- [ ] Execute Step 4 (Review) -> output: subagent_results/{phase}_review.md
- [ ] If Review FAILS -> Enter Fix Phase (F1-F5) -> max 3 retries
- [ ] Execute Step 5 (Doc Review) -> output: subagent_results/{phase}_doc_review.md
- [ ] If Doc Review FAILS -> Enter Fix Phase (F1-F5) -> max 3 retries
- [ ] Execute Step 6 (Experience) -> output: subagent_results/{phase}_experience.md
- [ ] Execute Step 7 (Controller Coordination) -> commit+push or next phase

## Phase Complete
- [ ] All 7 steps PASS
- [ ] Update docs/harness/PROJECT_CONTEXT.md
- [ ] Update openspec/changes/{active}/tasks.md
- [ ] Commit and push changes
- [ ] Clean up subagent_results/ if desired

# Core Principles

1. **OpenSpec is the only state anchor** - Do not create parallel documents
2. **Error management feeds OpenSpec** - Errors are input layer for state
3. **Main window compression recovery** - Use file records to restore context
4. **All agents share the same file system** - Consistent information access
5. **Controller NEVER implements code directly** - Always delegate [CODE] tasks
6. **Task type markers are mandatory** - [CODE]/[DOC]/[DATA]/[TEST]/[AUTO]
7. **Unmarked tasks default to [CODE]** - Safer delegation path
8. **Fix Phase before escalation** - 3 retries before giving up

# Related Skills

| Skill ID | Relationship | Purpose |
|----------|--------------|---------|
| skill_workflow_phase_loop | parent | Detailed 7-step workflow |
| skill_workflow_subagent_delegation | depends_on | Delegation rules for [CODE] tasks |
| skill_requirements_pm_style | depends_on | PM-style requirements template |
| skill_chat_review_decision_display | child | Chat UI pattern for review decisions |
| skill_chat_action_badge_colors | child | Visual indicators for actions |
| skill_chat_streamlit_multipage_handoff | child | Streamlit multipage patterns |

# Related Files

| File | Purpose |
|------|---------|
| AGENTS.md | Core rules and constraints for all agents |
| CONTROLLER_HARNESS_PRACTICE.md | Core principles in English |
| PROJECT_CONTEXT.md | Current state tracking |
| PHASE_LOOP.md | 7-step workflow definition |
| error_memory.jsonl | Error logging format |
| repair_playbook.md | Repair procedures for common errors |

# Changelog

| Version | Date | Change |
|---------|------|--------|
| 1.0.0 | 2026-05-08 | Initial creation - comprehensive master skill |
