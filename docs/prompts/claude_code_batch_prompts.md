# Claude Code Batch Prompts

## Overview

This document contains reusable prompt templates for implementing specific types of batches in an OpenSpec-driven development workflow using Claude Code. Each template is designed for a common batch pattern: schema/store implementation, standalone function implementation, optional entrypoint implementation, integration test batch, docs-only batch, and no-code planning batch.

Each prompt entry follows a consistent structure: purpose, when to use, inputs, forbidden scope, prompt template, expected output, acceptance checklist, and common failure modes.

---

## 1. Schema / Store Implementation Batch

### Purpose

Implement foundational data structures (Pydantic models, schemas, enums) and their associated storage layer. This is typically the first batch of any change because other components depend on the data contracts.

### When to Use

- When the first batch of a change needs to define data types and persistence
- When adding new Pydantic models, enums, or data transfer objects
- When implementing a storage layer (JSONL, database, in-memory)
- Before any business logic or pipeline integration

### Inputs to Provide

- **Design document**: The approved design.md defining the schemas and store
- **Spec document**: The spec.md with schema and store requirements
- **Existing schemas**: Current schema definitions for style consistency
- **Allowed files list**: Which files this batch can modify

### Forbidden Scope

- Do NOT implement business logic or pipeline integration
- Do NOT modify existing pipeline modules
- Do NOT add database migrations or schema changes
- Do NOT implement UI or display components
- Do NOT add external dependencies to pyproject.toml without explicit approval

### Prompt Template

```
I need to implement Batch 1: Schema/Store for [Change name].

**Design**: [path/to/design.md]
**Spec**: [path/to/spec.md]

**Allowed scope**:
- [File pattern 1, e.g., src/ticketpilot/schema/new_schema.py]
- [File pattern 2, e.g., src/ticketpilot/new_store.py]
- [File pattern 3, e.g., tests/unit/test_new_schema.py]
- [File pattern 4, e.g., tests/unit/test_new_store.py]

**Forbidden scope**:
- Do NOT modify: [existing pipeline files]
- Do NOT modify: [existing schema files]
- Do NOT modify: [any other file outside allowed scope]

**Existing schema patterns** (follow these conventions):
- [Link to existing schema file for style reference]
- [Naming conventions used]
- [Import patterns used]

**Existing store patterns** (follow these conventions):
- [Link to existing store file for style reference]
- [Testing patterns used]

Implement the following:

### Step 1: Define Schemas
- Create [SchemaName] Pydantic model(s) as defined in the design document
- Include all fields with proper types, defaults, and validators
- Follow existing naming conventions (same module, import, and class patterns)
- Use Optional[] for nullable fields, with documented defaults

### Step 2: Define Enums (if needed)
- Create enum classes for any fixed sets of values
- Use StrEnum or IntEnum as appropriate

### Step 3: Implement Store
- Create [StoreName] with the specified methods
- Follow existing store patterns (append-only, self-contained, inspectable)
- Use JSONL for MVP persistence unless DB storage is explicitly specified

### Step 4: Write Unit Tests
- Test each schema field: valid values, invalid values, defaults, edge cases
- Test each store method: save, load, count, edge cases (empty, corrupt data)
- Follow existing test patterns (file location, naming, fixtures)
- Mock external dependencies (file system, database)

### Step 5: Run Quality Gate
- After implementation: `bash scripts/run_quality_gate.sh`
- Quality gate must pass with:
  - Ruff: 0 errors
  - Unit tests: all pass, coverage >= [threshold]%
  - Integration tests: all pass, 0 skipped
  - Spec validation: all pass
  - Secret scan: clean

### Step 6: Commit
- Stage specific files only (NOT git add -A)
- Commit with message format: `type: [batch description]`
- Verify git status --short shows only expected files
```

### Expected Output

- New schema file(s) with Pydantic models and enums
- New store file with persistence methods (save, load, count)
- Unit tests covering all schema fields and store methods
- Quality gate passes (all stages)
- Batch committed with descriptive message
- tasks.md updated if needed

### Acceptance Checklist

- [ ] All Pydantic models match the design document specification
- [ ] Fields have proper types, defaults, and validators
- [ ] Enums use appropriate base class (StrEnum, IntEnum)
- [ ] Store implements all required methods (save, load, count)
- [ ] Store is append-only (no modification of written records)
- [ ] Unit tests cover: valid values, invalid values, defaults, edge cases
- [ ] Quality gate passes
- [ ] No files outside allowed scope were modified
- [ ] Commit message follows project conventions

### Common Failure Modes

- **Schema does not match design**: Pydantic model fields differ from the design document (wrong types, missing fields, extra fields). Verify each field against the design.
- **Missing validators**: Fields that need validation (string lengths, numeric ranges, format checks) are missing Pydantic validators.
- **Store not append-only**: The store modifies or deletes existing records instead of appending. Audit all write operations.
- **Insufficient test coverage**: Only testing the happy path for store methods. Test edge cases: empty store, corrupt data, concurrent writes.
- **Style inconsistency**: New schemas use different naming or import conventions than existing ones. Follow established patterns.

---

## 2. Standalone Function Implementation Batch

### Purpose

Implement a standalone function or module that performs a specific processing task. The function should be independently testable, have no side effects beyond its return value, and follow established patterns.

### When to Use

- When implementing a pure computation or transformation function
- When implementing a wrapper or composition function that wires existing components
- When implementing a validator, builder, or other stateless logic module
- When the function can be tested without a running database or external service

### Inputs to Provide

- **Design document**: The approved design.md defining the function
- **Spec document**: The spec.md with requirements and test scenarios
- **Existing function patterns**: Similar functions for style reference
- **Allowed files list**: Which files this batch can modify

### Forbidden Scope

- Do NOT modify the core pipeline or existing processing stages
- Do NOT add external dependencies
- Do NOT modify existing schemas (unless explicitly scoped)
- Do NOT implement UI or display components
- Do NOT add database calls (mock them in tests)

### Prompt Template

```
I need to implement Batch: Standalone Function for [Change name].

**Design**: [path/to/design.md]
**Spec**: [path/to/spec.md]

**Function to implement**: [Function name and signature]

**Allowed scope**:
- [File pattern 1, e.g., src/ticketpilot/new_module.py]
- [File pattern 2, e.g., tests/unit/test_new_module.py]

**Forbidden scope**:
- Do NOT modify: [existing pipeline files]
- Do NOT modify: [existing schema files]
- Do NOT modify: [any other file outside allowed scope]

**Existing function patterns** (follow these conventions):
- [Link to similar function for style reference]

Implement the following:

### Step 1: Implement the Function
- Create [Function name] as a standalone function (not a class unless required)
- Accept well-defined inputs, return well-defined outputs
- Handle edge cases: None inputs, empty collections, invalid values
- Raise appropriate exceptions for unrecoverable errors
- Document with docstring: purpose, args, returns, raises

### Step 2: Implement Error Handling
- All exceptions must be caught and handled or documented
- No unhandled crashes — function must never throw unexpected exceptions
- Return safe fallback values for recoverable errors

### Step 3: Write Unit Tests
- Test each logical path through the function
- Test with valid inputs (typical cases)
- Test with edge case inputs (empty, None, boundary values)
- Test with invalid inputs (wrong types, out-of-range values)
- Test error handling paths (exception scenarios)
- Mock external dependencies (if any)

### Step 4: Run Quality Gate
- After implementation: `bash scripts/run_quality_gate.sh`
- All stages must pass

### Step 5: Commit
- Stage specific files only
- Commit with message format: `type: [batch description]`
- Verify git status --short shows only expected files
```

### Expected Output

- New standalone function(s) with proper error handling and documentation
- Unit tests covering: typical cases, edge cases, invalid inputs, error paths
- Quality gate passes
- Batch committed with descriptive message

### Acceptance Checklist

- [ ] Function signature matches the design document
- [ ] All edge cases are handled (empty, None, boundary, invalid)
- [ ] No unhandled exceptions (graceful fallback for recoverable errors)
- [ ] Docstring documents purpose, args, returns, raises
- [ ] Unit tests cover all logical paths
- [ ] Mocking is used for external dependencies (DB, network, filesystem)
- [ ] Quality gate passes
- [ ] No files outside allowed scope were modified

### Common Failure Modes

- **Incomplete edge case handling**: Function works for typical inputs but crashes on empty or None values. Test with None, empty strings, empty lists.
- **No error handling**: A function that assumes valid input and crashes on anything else. Wrap external calls and document exception behavior.
- **Side effects**: The function modifies global state, writes to files, or changes module-level variables. Pure functions should have no side effects.
- **Too large**: A single "standalone function" that does too many things. If it needs sub-functions, create a module, not a monolithic function.
- **Insufficient test coverage**: Testing only the happy path. Every branch (if/else, try/except) should have a dedicated test case.

---

## 3. Optional Entrypoint Implementation Batch

### Purpose

Implement an optional workflow entrypoint that composes existing pipeline functionality with new functionality without modifying the core pipeline. This pattern is used when adding features that should be opt-in for consumers.

### When to Use

- When adding an optional stage or workflow that layers on top of an existing pipeline
- When creating a wrapper function that combines existing processing with new processing
- When the new functionality should NOT modify the core pipeline contract
- When existing consumers must continue working without changes

### Inputs to Provide

- **Design document**: The approved design.md describing the optional workflow
- **Core pipeline interface**: The existing pipeline function that must NOT change
- **Existing consumer list**: Who uses the core pipeline and how
- **Allowed files list**: Which files this batch can modify

### Forbidden Scope

- Do NOT modify the core pipeline function(s)
- Do NOT change the return type of existing functions
- Do NOT add optional parameters to existing functions
- Do NOT modify existing consumer code to use the new entrypoint
- Do NOT make the optional workflow the default behavior

### Prompt Template

```
I need to implement Batch: Optional Entrypoint for [Change name].

**Design**: [path/to/design.md]
**Spec**: [path/to/spec.md]

**Core pipeline function (DO NOT MODIFY)**:
[Function name and signature]

**New functionality to compose**: [Brief description]

**Allowed scope**:
- [File pattern for new entrypoint]
- [File pattern for tests of new entrypoint]
- [Any export/init file changes needed]

**Forbidden scope**:
- Do NOT modify: [core pipeline file]
- Do NOT modify: [existing consumer files]
- Do NOT modify: [any other file outside allowed scope]

Implement the following:

### Step 1: Create Wrapper Type (if needed)
- Create a narrow wrapper type that combines core output + new output
- The wrapper should NOT abstract or replace the core output type
- Consumers who need the core output must be able to access it directly

### Step 2: Implement the Optional Entrypoint
- Create a new function that calls the core pipeline then applies new functionality
- The new function must have a distinct, descriptive name
- The new function must NOT modify the core pipeline's output
- Error handling: if the new functionality fails, return the core output with a fallback indicator
- The core pipeline's behavior must be unchanged

### Step 3: Verify Backward Compatibility
- [ ] Core pipeline import path is unchanged
- [ ] Core pipeline function signature is unchanged
- [ ] Core pipeline return type is unchanged
- [ ] Existing consumer code needs NO modifications
- [ ] New entrypoint is opt-in (consumers must explicitly import and call it)

### Step 4: Write Unit Tests
- Test the optional entrypoint with varied inputs
- Test fallback behavior (when new functionality fails)
- Test that core pipeline is NOT modified by the wrapper
- Test that the wrapper type is transparent (core output is accessible)

### Step 5: Run Quality Gate
- After implementation: `bash scripts/run_quality_gate.sh`
- All stages must pass

### Step 6: Commit
- Stage specific files only
- Commit with message format: `type: [batch description]`
- Verify git status --short shows only expected files
```

### Expected Output

- New optional entrypoint function(s) that compose core pipeline + new functionality
- Wrapper type (if needed) that is narrow and transparent
- Unit tests covering: entrypoint behavior, fallback, core pipeline unaffected
- Quality gate passes
- Backward compatibility verified

### Acceptance Checklist

- [ ] Core pipeline function is NOT modified
- [ ] Core pipeline return type is NOT changed
- [ ] Existing consumers need NO code changes
- [ ] New entrypoint is opt-in (explicit import/call required)
- [ ] Wrapper type (if created) is transparent (core output accessible)
- [ ] Error handling: new functionality failure returns fallback, not crash
- [ ] Quality gate passes
- [ ] No files outside allowed scope were modified

### Common Failure Modes

- **Modifying the core pipeline**: Adding a parameter, changing the return type, or adding conditional logic to the core pipeline. This breaks the existing contract.
- **Wrapper type hides core output**: The wrapper type doesn't expose the core pipeline's output, forcing consumers to change their code to access it.
- **Entrypoint not truly optional**: If the new entrypoint is called from core pipeline code or imported in __init__.py of the core module, it's not optional.
- **Fallback not implemented**: If the new functionality raises an exception, the entire pipeline crashes instead of returning the core output with a fallback.
- **No backward compatibility test**: Assuming existing consumers work without verifying. Run existing tests to confirm no regressions.

---

## 4. Integration Test Batch

### Purpose

Create or expand integration tests that verify end-to-end behavior against a live database. Integration tests are the final verification layer before documentation and archive.

### When to Use

- When a change needs end-to-end verification against a real database
- When unit tests alone cannot verify pipeline integration
- After all implementation batches are complete
- Before the final quality gate and archive

### Inputs to Provide

- **Design document**: The approved design.md for context
- **Existing integration tests**: Current integration test patterns to follow
- **Test scenarios**: What end-to-end scenarios need verification
- **Database setup**: How the test database is configured and seeded

### Forbidden Scope

- Do NOT modify production code (this is a test-only batch)
- Do NOT add browser automation tests (unless explicitly scoped)
- Do NOT add tests that require unavailable external services
- Do NOT add tests that are not repeatable (non-deterministic assertions)
- Do NOT skip integration tests — all must pass with 0 skips

### Prompt Template

```
I need to implement the integration test batch for [Change name].

**Design**: [path/to/design.md]
**Spec**: [path/to/spec.md]

**Allowed scope**:
- [File pattern for new integration tests]
- [Any test fixtures needed]

**Forbidden scope**:
- Do NOT modify any production code in src/
- Do NOT modify existing unit tests (unless explicitly scoped)
- Do NOT modify the quality gate script

**Existing integration test patterns** (follow these conventions):
- [Link to existing integration test file]
- [Fixtures, markers, and setup patterns used]
- [Seed data used]

**Test scenarios to verify**:
- [Scenario 1]: [What it verifies and expected result]
- [Scenario 2]: [What it verifies and expected result]
- [Scenario 3]: [What it verifies and expected result]

Implement the following:

### Step 1: Set Up Test Fixtures
- Use existing database seed data (or add new seed data if needed)
- Follow existing fixture patterns (conftest.py, pytest fixtures, markers)

### Step 2: Write Integration Tests
- Each test should verify a specific end-to-end scenario
- Assert on: pipeline output types, field values, database state
- Cover: typical cases, edge cases, error cases, safety behaviors
- Verify: no auto-send, must-human-review propagation, citation validation

### Step 3: Verify Database Independence
- Tests must work with seed data loaded in the live database
- Tests must clean up after themselves (no test pollution)
- Tests must pass with 0 skips

### Step 4: Run Quality Gate
- Ensure database is running: `docker compose up -d`
- Run: `bash scripts/run_quality_gate.sh`
- Verify: 0 integration test failures, 0 skipped

### Step 5: Commit
- Stage specific files only (test files only)
- Commit with message format: `test: [batch description]`
- Verify git status --short shows only expected files
```

### Expected Output

- New integration test file(s) covering end-to-end scenarios
- Tests that verify pipeline behavior against a live database
- All tests pass with 0 skipped
- Quality gate passes

### Acceptance Checklist

- [ ] Integration tests verify end-to-end behavior against live database
- [ ] Tests cover: typical cases, edge cases, error cases, safety behaviors
- [ ] No production code was modified
- [ ] All tests pass with 0 skipped
- [ ] Tests are independent (no test pollution, can run in any order)
- [ ] Quality gate passes
- [ ] No files outside allowed scope were modified

### Common Failure Modes

- **Tests skip because DB is unavailable**: Always start the database before running integration tests. Use `docker compose up -d` and wait for readiness.
- **Test pollution**: One test modifies shared state that affects subsequent tests. Each test should be independent and clean up after itself.
- **Non-deterministic assertions**: Tests that assert on ordering, timing, or random values. Use deterministic comparisons.
- **Too few scenarios**: Only testing the happy path. Include edge cases, error handling, and safety behavior verification.
- **Modifying production code**: Integration test batch should NOT modify any src/ files. If you need production code changes, they go in a separate batch.

---

## 5. Docs-Only Batch

### Purpose

Create or update documentation files only — no production code changes, no test changes (unless documentation tests). This is used for changelog updates, phase status updates, and pure documentation additions.

### When to Use

- When updating changelog.md or phase_status.md
- When creating new documentation (development trace, technical docs, skills, prompts)
- When updating documentation to reflect completed implementation
- When no code changes are needed

### Inputs to Provide

- **Documentation plan**: What documents to create or modify
- **Content sources**: Where to get the information for the documents
- **Documentation standards**: Format, style, and conventions to follow
- **Files to modify**: Specific documentation file paths

### Forbidden Scope

- Do NOT modify any production code in src/
- Do NOT modify any test code in tests/
- Do NOT modify configuration files (pyproject.toml, docker-compose.yml)
- Do NOT add code snippets that claim capabilities that don't exist
- Do NOT make unsubstantiated claims about production readiness

### Prompt Template

```
I need to implement a documentation-only batch for [Change name].

**Documentation plan**:
- [File 1]: [Purpose and content summary]
- [File 2]: [Purpose and content summary]
- [File 3]: [Purpose and content summary]

**Content sources**:
- [Source 1]: [What information to extract]
- [Source 2]: [What information to extract]
- [Source 3]: [What information to extract]

**Allowed scope**:
- [docs/file1.md]
- [docs/file2.md]

**Forbidden scope**:
- Do NOT modify any src/ files
- Do NOT modify any tests/ files
- Do NOT modify configuration files

**Truth-in-documentation rules** (apply to every document):
1. [ ] Fake/prototype components labeled clearly as non-production
2. [ ] No claim of capabilities that don't exist
3. [ ] Test counts are exact (not rounded or estimated)
4. [ ] Deferred items are documented where relevant
5. [ ] No aspirational language about future capabilities
6. [ ] Commit SHAs are used (not "recent" or "latest")
7. [ ] Product boundary constraints are respected

Implement the following:

### Step 1: Create/Update Documents
- For each file: follow the existing documentation structure and style
- Extract information from the specified content sources
- Apply truth-in-documentation rules to every document
- Include exact test counts, commit SHAs, and verifiable facts

### Step 2: Verify Documentation Consistency
- Cross-reference: do all documents agree on test counts, dates, and facts?
- Check: are all deferred items listed in the same way across documents?
- Verify: do documents reference actual files that exist?

### Step 3: Run Quality Gate (if applicable)
- Documentation-only batches may skip quality gate if no code or test changes
- If any Python or test files are touched, quality gate is required

### Step 4: Commit
- Stage documentation files only
- Commit with message format: `docs: [batch description]`
- Verify git status --short shows only expected files
```

### Expected Output

- Created or updated documentation files
- All truth-in-documentation rules applied
- Documentation consistency verified across files
- Commit with descriptive message

### Acceptance Checklist

- [ ] All planned documents are created or updated
- [ ] Truth-in-documentation rules applied to every document
- [ ] No src/ or tests/ files were modified
- [ ] No configuration files were modified
- [ ] All facts (test counts, SHAs, dates) are verified against source material
- [ ] Documentation is internally consistent (no contradictory facts)
- [ ] Commit message follows project conventions

### Common Failure Modes

- **Adding code snippets in docs batch**: A documentation batch that modifies src/ or tests/ files. Keep docs-only batches strictly docs-only.
- **Factual errors**: Test counts don't match quality gate output, commit SHAs are wrong, dates are incorrect. Always verify facts against source material.
- **Unsupported claims**: Saying "the system has LLM-powered generation" when using a template-based fake provider. Use precise, verifiable language.
- **Inconsistent deferred items**: One document lists 5 deferred items while another lists 10. Maintain a single source of truth.
- **Missing truth labels**: Fake embeddings, synthetic data, and other limitations must be labeled wherever mentioned.

---

## 6. No-Code Planning Batch

### Purpose

Create or update planning documents only — proposals, designs, specs, and tasks — without writing any implementation code. This establishes the blueprint before any code is written.

### When to Use

- At the start of a new OpenSpec change (creating proposal, design, spec, tasks)
- When reviewing and updating an existing design before implementation
- When documenting design decisions and architecture
- Before any implementation batch begins

### Inputs to Provide

- **Problem statement**: What needs to be solved
- **Existing architecture context**: Current system state
- **Constraints**: Quality gate, product boundary, provider limitations
- **Reviewers available**: Which roles will review the design

### Forbidden Scope

- Do NOT write any implementation code
- Do NOT modify any src/ files
- Do NOT modify any tests/ files
- Do NOT modify configuration files
- Do NOT run the quality gate (no code to test)

### Prompt Template

```
I need to create a planning batch for [Change name].

**Problem**: [Description of the problem or requirement]

**Existing context**:
- [Current architecture]
- [Prior decisions that apply]
- [Constraints that apply]

**Allowed scope**:
- openspec/changes/[Change-name]/proposal.md (create)
- openspec/changes/[Change-name]/design.md (create)
- openspec/changes/[Change-name]/spec.md (create)
- openspec/changes/[Change-name]/tasks.md (create)

**Forbidden scope**:
- Do NOT write any implementation code
- Do NOT modify src/, tests/, or configuration files

Use the spec-driven development process:

1. **Propose**: Create proposal.md with:
   - Problem statement
   - Proposed approach
   - Value proposition
   - Explicit out-of-scope items
   - Key constraints

2. **Design**: Create design.md with:
   - Architecture diagram or description
   - Data flow
   - Data contracts (schemas, interfaces)
   - Key design decisions with rationale and alternatives
   - Risk assessment

3. **Specify**: Create spec.md with:
   - Requirements with Gherkin-style scenarios (WHEN/THEN)
   - Test strategy (unit and integration)
   - Concrete acceptance thresholds
   - What is explicitly NOT tested

4. **Plan**: Create tasks.md with:
   - Phase and batch breakdown
   - Each batch: allowed scope, forbidden scope, test count estimates
   - Dependency order (foundation before dependent)
   - Documentation and finalization phases

Design review requirements:
- Present the design for review by system-architect
- Present the test strategy for review by qa-evaluator
- Present the scope for review by project-director
- Present the plan for review by phase-supervisor
- Incorporate feedback before proceeding to implementation

Truth-in-documentation rules:
- Do NOT claim capabilities that don't exist
- Do NOT propose features outside the product boundary
- Do NOT exaggerate maturity or readiness
- Use precise, verifiable language
```

### Expected Output

- An OpenSpec change directory with proposal.md, design.md, spec.md, and tasks.md
- Evidence of review by all four roles
- No code written or modified
- A clear path to implementation (batch breakdown)

### Acceptance Checklist

- [ ] proposal.md clearly states the problem, approach, and out-of-scope items
- [ ] design.md includes architecture, data flow, key decisions, and alternatives
- [ ] spec.md has requirements with Gherkin scenarios and test strategy
- [ ] tasks.md has batch breakdown with allowed/forbidden scope
- [ ] No src/, tests/, or configuration files were modified
- [ ] Design has been reviewed by all four roles
- [ ] Product boundary is respected
- [ ] No unsubstantiated claims about capabilities

### Common Failure Modes

- **Skipping the review step**: Creating all documents but not getting formal review from each role. Review is the most valuable part of this phase.
- **Design too vague**: "The system will process data" with no specifics on how, what types, or what transformations. Push for concreteness.
- **Spec without acceptance criteria**: Requirements without measurable pass conditions. Each requirement should have a WHEN/THEN scenario.
- **Tasks too large**: Batches that are too large to implement and review in a reasonable timeframe. If a batch touches 10+ files, split it.
- **Missing forbidden scope**: Tasks that don't say what each batch must NOT touch. Forbidden scope is as important as allowed scope.
- **Over-engineering**: Designing for hypothetical future needs instead of current requirements. Design for what you're building now.

---

## Prompt Index

| Prompt | Purpose | When to Use |
|--------|---------|-------------|
| Schema/Store Implementation | Implement data structures and persistence | First batch of any change |
| Standalone Function Implementation | Implement pure computation/transformation function | Stateless logic, wrappers, validators |
| Optional Entrypoint Implementation | Create optional workflow on top of existing pipeline | Additive features, non-breaking changes |
| Integration Test Batch | Create end-to-end tests against live database | After implementation, before docs |
| Docs-Only Batch | Create or update documentation files | Changelog, phase status, docs creation |
| No-Code Planning Batch | Create proposal, design, spec, tasks | Change inception, pre-implementation |
