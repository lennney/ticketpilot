# Project Director Prompts

## Overview

This document contains reusable prompt templates for the **Project Director** role in an OpenSpec-driven development workflow. The Project Director is responsible for product strategy, scope definition, roadmap planning, and preventing feature creep. These prompts help structure the conversation with a Project Director agent (or human role) across different decision points in a project lifecycle.

Each prompt entry follows a consistent structure: purpose, when to use, inputs, forbidden scope, prompt template, expected output, acceptance checklist, and common failure modes.

---

## 1. Creating a New OpenSpec Change

### Purpose

Propose and scaffold a new OpenSpec change with a clear problem statement, approach, and initial task breakdown. This is the first step in the spec-driven development lifecycle.

### When to Use

- Starting a new feature or non-trivial enhancement
- Making a change that could affect multiple modules or introduce new data contracts
- Adding a new pipeline stage, provider, or integration point
- Do NOT use for trivial bug fixes, typo corrections, or documentation-only changes that have no spec impact

### Inputs to Provide

- **Problem statement**: A clear description of what problem is being solved
- **Affected modules**: Which parts of the existing system would be touched
- **Constraints**: Any architectural, quality gate, or product boundary constraints that apply
- **Existing context**: Links to related OpenSpec changes, technical docs, or design notes

### Forbidden Scope

- Do NOT write implementation code before the spec is approved
- Do NOT skip the proposal or design phase for changes that affect multiple modules
- Do NOT propose changes that violate the established product boundary
- Do NOT propose changes requiring capabilities known to be deferred or unavailable
- Do NOT make unsubstantiated claims about production readiness, retrieval quality, or data coverage

### Prompt Template

```
I need to propose a new OpenSpec change for [Project name].

**Problem**: [Describe the problem or requirement]

**Affected areas**: [List modules, schemas, pipelines, or configurations that would change]

**Key constraints**:
- [Constraint 1, e.g., "No auto-send"]
- [Constraint 2, e.g., "Fake providers only for MVP"]
- [Constraint 3, e.g., "Quality gate requires >= 70% coverage, 0 skipped integration tests"]

**Out of scope (explicitly)**: [What this change does NOT include]

Walk through the following process:

1. **Explore** — Use an exploration process (e.g., openspec explore) to investigate the
   problem space, existing constraints, and potential approaches. Identify all modules
   that would be affected.

2. **Propose** — Create the change directory with:
   - `proposal.md`: Problem, approach, value, what is out of scope
   - `design.md`: Architecture, data flow, key design decisions, alternatives considered
   - `spec.md`: Requirements with Gherkin-style scenarios (WHEN/THEN), test strategy,
     concrete acceptance thresholds
   - `tasks.md`: Phase and batch breakdown with allowed/forbidden scope per batch

3. **Review** — Present the design for review by system-architect, qa-evaluator, and
   phase-supervisor roles. Incorporate feedback before finalizing.

Do NOT write implementation code at this stage.
Do NOT use vague acceptance criteria — each criterion must have a concrete, measurable
pass condition.
```

### Expected Output

- An OpenSpec change directory at `openspec/changes/[Change-name]/` containing:
  - `proposal.md` with problem statement, approach, value proposition, and explicit out-of-scope items
  - `design.md` with architecture, data flow, key decisions, alternatives, and constraints
  - `spec.md` with requirements, Gherkin scenarios, and test strategy
  - `tasks.md` with phases and batches, each with allowed/forbidden scope
- A review record showing feedback from system-architect, qa-evaluator, and phase-supervisor

### Acceptance Checklist

- [ ] Change directory exists at `openspec/changes/[Change-name]/` with all four artifacts
- [ ] `proposal.md` clearly states the problem, approach, and what is out of scope
- [ ] `design.md` includes architecture, data flow, design decisions, and alternatives
- [ ] `spec.md` has requirements with Gherkin scenarios and measurable acceptance criteria
- [ ] `tasks.md` defines phases and batches with allowed/forbidden scope per batch
- [ ] No implementation code exists in the change directory
- [ ] Design has been reviewed by all applicable agent roles
- [ ] Product boundary is respected (no generic functionality, no auto-action)
- [ ] No unsubstantiated claims about production readiness or unavailable capabilities

### Common Failure Modes

- **Skipping the design phase**: Proceeding directly from idea to tasks leads to requirement drift. The design document is the cheapest place to catch mistakes.
- **Vague acceptance criteria**: "Works correctly" is not testable. Each criterion must have a concrete, measurable pass condition.
- **Product boundary violations**: Proposing features that turn the system into something outside its defined scope. Apply domain-appropriate boundary tests.
- **Unsubstantiated claims**: Saying a capability exists when it does not. Use precise, verifiable language about current capabilities.
- **Over-scoping**: Trying to solve too many problems in one change. Split large changes into smaller, independently valuable increments.

---

## 2. Defining Product Boundary

### Purpose

Establish and communicate what the product IS and what it IS NOT. This prevents scope creep and maintains focused product identity during development.

### When to Use

- At project inception to define the product's core identity
- When evaluating a new feature request or change proposal
- When reviewing design documents for scope compliance
- When onboarding new contributors to the project
- When responding to "why doesn't the product do X?" questions

### Inputs to Provide

- **Product description**: One-sentence definition of the product
- **Current capabilities**: What the system currently does
- **Target domain**: The specific domain or use case the product addresses
- **Architecture summary**: The pipeline stages or processing layers that define the product

### Forbidden Scope

- Do NOT allow features that turn the product into a generic tool outside its domain
- Do NOT allow auto-action or bypassing human review
- Do NOT allow features that would require unavailable capabilities
- Do NOT claim production readiness, real semantic retrieval quality, or real enterprise data coverage

### Prompt Template

```
I need to define the product boundary for [Project name].

**Product definition**: [One-sentence description]

**Current capabilities**:
- [Capability 1]
- [Capability 2]
- [Capability 3]

**Architecture**: [Brief description of the pipeline or processing stages]

**Proposed feature**: [Description of the feature being evaluated]

Apply domain-appropriate boundary tests (customize these for your product):

1. **Generic [domain] test**: Does this feature allow open-ended use outside the
   defined domain? If yes, reject.

2. **[Domain] knowledge test**: Does this feature allow querying arbitrary knowledge
   outside the defined knowledge types? If yes, reject.

3. **Auto-action test**: Does this feature dispatch actions or trigger external
   processes without human approval? If yes, reject.

Then evaluate:
- Does it fit within the defined product capabilities?
- Does it require capabilities known to be unavailable?
- Does it make claims that exceed documented system maturity?

Provide a clear **IN SCOPE / OUT OF SCOPE** decision with rationale.

If IN SCOPE, also provide:
- What constraints must be documented in the change design
- What limitations or deferred items must be explicitly noted
```

### Expected Output

- A clear **IN SCOPE** or **OUT OF SCOPE** decision with supporting rationale
- If IN SCOPE: design constraints to be included in the change, limitations to document
- If OUT OF SCOPE: specific boundary test that failed, explanation of why
- Optional: guidance on how to reframe the feature to fit within the product boundary

### Acceptance Checklist

- [ ] Decision is unambiguous (IN SCOPE or OUT OF SCOPE)
- [ ] Rationale references specific boundary tests or constraints
- [ ] No unsubstantiated claims about capability or maturity
- [ ] If IN SCOPE: design constraints are clearly specified
- [ ] If OUT OF SCOPE: explanation references specific boundary principle

### Common Failure Modes

- **"It's just a small extension"**: Adding a small feature outside the product boundary is still a violation. The slope from "small extension" to "completely different product" is slippery.
- **Boundary test not applicable**: Adapt the boundary tests to the product's core identity. The tests are domain-specific, not universal.
- **Claiming more than delivered**: Use precise language about current capabilities versus planned capabilities.
- **Overlooking subtle boundary violations**: A feature may pass the literal boundary test but violate the spirit of the product constraint. Consider intent as well as wording.

---

## 3. Splitting Roadmap into Stages

### Purpose

Break a product vision into independently valuable, sequentially deliverable stages, each with clear acceptance criteria and explicit out-of-scope items.

### When to Use

- At project inception when planning the overall roadmap
- After completing one major stage and planning the next
- When prioritizing which features to build and in what order
- When stakeholders ask for delivery timelines

### Inputs to Provide

- **Product vision**: The long-term goal for the product
- **Product boundary**: What the product is and is not
- **Known constraints**: Technical, quality, or domain constraints
- **Deferred items**: Known capabilities that are out of scope for the current phase

### Forbidden Scope

- Do NOT include stages that violate the product boundary
- Do NOT include stages that require capabilities known to be unavailable without a plan to acquire them
- Do NOT create stages that are too large to deliver in a reasonable timeframe
- Do NOT make commitments about future stages that may change based on learning

### Prompt Template

```
I need to split the product roadmap for [Project name] into stages.

**Product vision**: [Long-term goal]

**Product boundary**: [Core identity, what it is and is not]

**Known constraints**:
- [Technical constraint 1]
- [Quality constraint 1]
- [Domain constraint 1]

**Deferred items** (known out of scope for now):
- [Item 1]
- [Item 2]

Define stages following these principles:

1. **Each stage delivers independent value** — A stage should be usable and
   demonstrable on its own, even if later stages are never built.

2. **Stages build on each other** — Stage N should not require rework when Stage N+1
   is added. Forward-compatible design within reason.

3. **Stage scope is bounded** — Each stage should be achievable in weeks, not months.
   If a stage is too large, split it.

4. **Clear exit criteria** — Each stage must have concrete, measurable acceptance
   criteria tied to test counts, coverage thresholds, and quality gate results.

5. **Explicit out-of-scope** — Each stage must document what it does NOT include, to
   prevent scope creep.

Produce:
- Stage overview table: name, description, expected duration, dependencies
- Per stage: goal, scope (what is included), explicit out-of-scope, acceptance
  criteria, key risks
- Dependency map showing which stages depend on which
```

### Expected Output

- A stage overview table with name, description, expected duration, and dependencies
- Per-stage documentation: goal, included scope, explicit out-of-scope, acceptance criteria, risks
- A dependency graph or sequence showing stage ordering
- Guidance on what to do if a stage proves too large (split strategy)

### Acceptance Checklist

- [ ] Each stage delivers independently valuable functionality
- [ ] Stages are ordered by dependency (foundation before dependent work)
- [ ] No stage is too large to deliver in a reasonable timeframe
- [ ] Each stage has concrete, measurable acceptance criteria
- [ ] Each stage has explicit out-of-scope items
- [ ] Product boundary is respected across all stages
- [ ] Known deferred items are documented and not included in early stages
- [ ] The roadmap is realistic given available resources and constraints

### Common Failure Modes

- **Stages that are too large**: A stage that takes months to deliver creates risk and delayed feedback. Break it into smaller stages.
- **Stages with no independent value**: If a stage's output cannot be demonstrated or used until the next stage is built, the boundary is wrong.
- **Missing out-of-scope documentation**: Without explicit out-of-scope for each stage, scope creep is inevitable.
- **Unrealistic dependencies**: Stage N+1 should not require significant rework of Stage N. Design interfaces between stages carefully.
- **Planning too far ahead**: Detailed plans beyond 2-3 stages are likely to become obsolete. Use rolling-wave planning: detailed for the next stage, outline for the rest.

---

## 4. Preventing Scope Creep

### Purpose

Detect and block scope creep during implementation by comparing proposed additions against the approved change scope, product boundary, and established constraints.

### When to Use

- During implementation when a developer suggests adding "just one more thing"
- During design review when a feature is broader than the approved scope
- During acceptance review when the implementation includes unapproved functionality
- At any point when the change's scope boundary is being stretched

### Inputs to Provide

- **Change scope**: The approved allowed and forbidden scope for the current change or batch
- **Product boundary**: What the product is and is not
- **Proposed addition**: The feature, change, or extension being evaluated
- **Current constraints**: Quality gate, architecture, or domain constraints

### Forbidden Scope

- Do NOT approve scope creep that violates the approved change scope
- Do NOT approve scope creep that violates the product boundary
- Do NOT approve scope creep that adds capabilities known to be deferred
- Do NOT allow exceptions based on "it's small" or "I'll do it quickly"

### Prompt Template

```
I need to evaluate whether a proposed addition is scope creep.

**Current change**: [Change name]
**Approved scope**: [What the change is supposed to deliver]
**Forbidden scope**: [What the change explicitly does NOT include]

**Proposed addition**: [Description of the extra feature or change]
**Rationale**: [Why it is being proposed]

**Product boundary** (if applicable):
- Does the addition fit within the product's core identity?
- Does it violate any boundary constraints?

**Current constraints**:
- [Quality gate threshold]
- [Provider limitations]
- [Architectural constraints]

Evaluate:

1. **Scope test**: Is this within the approved scope of the current change?
2. **Boundary test**: Does it violate the product boundary?
3. **Deferred test**: Is this something explicitly deferred or planned for a later stage?
4. **Necessity test**: Is this required for the current change to function correctly?

Decision framework:
- If it fails scope test: REJECT. Move to a future change or create a new change.
- If it fails boundary test: REJECT. Document why the product boundary was violated.
- If it fails deferred test: REJECT. It belongs in a later stage.
- If it passes all tests AND is necessary for correctness: APPROVE with caveat that
  scope documentation is updated.
- If it passes all tests but is not necessary for correctness: DEFER. Create a
  follow-up task or change.
```

### Expected Output

- A clear decision: APPROVE, REJECT, or DEFER
- Rationale referencing the specific test that was failed or passed
- If DEFER: a suggestion for where the addition belongs (future change, follow-up task)
- If REJECT: documentation of why and what to do instead

### Acceptance Checklist

- [ ] Decision is clear and unambiguous
- [ ] Rationale references specific scope or boundary criteria
- [ ] Rejected additions are documented with reason and alternative pathway
- [ ] Approved additions are accompanied by scope documentation updates
- [ ] No "it's just small" exceptions allowed without scope change approval

### Common Failure Modes

- **"While I'm here" syndrome**: The most common source of scope creep. Fix only what is in the approved scope.
- **"It's required for correctness" false claim**: Adding a utility function may be required; adding a new feature is not. Distinguish between implementation detail and feature expansion.
- **Scope documentation not updated**: If an addition is approved, the scope documentation must be updated immediately. Otherwise the scope boundary becomes unreliable.
- **Mixing deferred and current scope**: "We'll need this later" should result in deferral, not early implementation. Early implementation adds risk with no immediate value.

---

## 5. Selecting Next Phase Without Overbuilding

### Purpose

Determine which phase or batch to work on next, ensuring that work is selected based on dependency order, risk reduction, and value delivery — not on which task is most interesting.

### When to Use

- After completing a phase or batch and selecting the next one
- When planning a new implementation cycle
- When prioritizing among multiple candidate changes or features
- When deciding whether to start a new change or continue refining an existing one

### Inputs to Provide

- **Completed phases**: What has been finished and accepted
- **Remaining phases**: What has not started or is in progress
- **Open risks**: Known risks that may affect the next phase
- **Dependency map**: Which phases depend on which

### Forbidden Scope

- Do NOT select a phase that depends on uncompleted prior work
- Do NOT select a phase that exceeds the current resource or time budget
- Do NOT select a phase that requires capabilities known to be unavailable
- Do NOT skip risk-reduction work in favor of more interesting work

### Prompt Template

```
I need to select the next development phase for [Project name].

**Current state**: [What has been completed and accepted]
**Remaining work**:
- [Phase/batch 1]: [Brief description]
- [Phase/batch 2]: [Brief description]
- [Phase/batch 3]: [Brief description]

**Dependencies**:
- [Phase X] must be done before [Phase Y]
- [Phase Z] requires [Capability]

**Known risks**:
- [Risk 1]
- [Risk 2]

**Selection criteria** (in priority order):
1. **Dependency resolution**: Select phases that unblock other work.
2. **Risk reduction**: Select phases that reduce the biggest risks earliest.
3. **Value delivery**: Select phases that deliver independently usable value.
4. **Effort estimation**: Select phases that can be completed in available time.

Apply the criteria:

1. Which phases are blocked by uncompleted prior work? (Eliminate these.)
2. Which phases unblock the most downstream work? (Prioritize these.)
3. Which phases reduce the highest-risk items? (Prioritize these.)
4. Among the remaining candidates, which delivers the most value for the least effort?

Provide:
- Selected next phase
- Rationale referencing the selection criteria
- What conditions would trigger a different selection
- Explicit "what we are NOT doing next" (to prevent scope drift)
```

### Expected Output

- Selected next phase with rationale referencing selection criteria
- Explanation of why other phases were not selected
- Conditions that would change the selection
- Explicit list of what is NOT being done next

### Acceptance Checklist

- [ ] Selected phase does not depend on uncompleted prior work
- [ ] Rationale references at least two of the four selection criteria
- [ ] Non-selected phases have documented reasons for deferral
- [ ] No selection based solely on interest or convenience
- [ ] Risk-reduction phases are prioritized when risks are high

### Common Failure Modes

- **Selecting the most interesting work instead of the most important**: Interest is not a selection criterion. Follow the criteria in priority order.
- **Ignoring dependencies**: Selecting a phase that requires uncompleted prior work leads to blockers and rework.
- **Skipping risk reduction**: High-risk items should be tackled early, not deferred until the end when there is no time to fix them.
- **Overbuilding**: Building more than needed for the current phase. "We'll need it later" is not a reason to include it now.
- **Not documenting what is NOT being done**: Without explicit exclusion, stakeholders may assume everything is being worked on simultaneously.

---

## Prompt Index

| Prompt | Purpose | When to Use |
|--------|---------|-------------|
| Creating a New OpenSpec Change | Scaffold a new change with proposal, design, spec, tasks | Starting new feature or non-trivial enhancement |
| Defining Product Boundary | Establish what the product is and is not | Project inception, feature evaluation, scope compliance |
| Splitting Roadmap into Stages | Break vision into deliverable stages | Roadmap planning, stage completion |
| Preventing Scope Creep | Detect and block unapproved scope expansion | Implementation, design review, acceptance review |
| Selecting Next Phase Without Overbuilding | Choose next work based on dependency, risk, value | Phase completion, planning cycle |
