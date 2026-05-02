# System Architect Prompts

## Overview

This document contains reusable prompt templates for the **System Architect** role in an OpenSpec-driven development workflow. The System Architect is responsible for reviewing architecture decisions, data contracts, integration boundaries, provider abstractions, and workflow designs. These prompts help structure architecture reviews at key decision points in the development lifecycle.

Each prompt entry follows a consistent structure: purpose, when to use, inputs, forbidden scope, prompt template, expected output, acceptance checklist, and common failure modes.

---

## 1. Architecture Review

### Purpose

Review the overall system architecture of a proposed change, evaluating whether the design is sound, consistent with existing patterns, and appropriately bounded. This is typically the first review step after a design document is created.

### When to Use

- When a new OpenSpec change has a draft `design.md` ready for review
- When proposing a significant refactoring or re-architecture
- When integrating a new subsystem or external dependency
- When the existing architecture documentation needs validation

### Inputs to Provide

- **Change design**: Link to the `design.md` from the OpenSpec change
- **Existing architecture docs**: Current system architecture documentation
- **Technical decisions record**: Prior decisions that constrain this design
- **Quality gate requirements**: Thresholds that must be maintained

### Forbidden Scope

- Do NOT review implementation details (code-level concerns)
- Do NOT review test coverage (this is QA scope)
- Do NOT make product scope decisions (this is Project Director scope)
- Do NOT review individual function signatures (focus on module interfaces)
- Do NOT claim capabilities that do not exist

### Prompt Template

```
I need you to review the architecture for this proposed change.

**Change**: [Change name]
**Design document**: [path/to/design.md]

**Existing architecture context**:
- [Relevant architecture documentation links]
- [Key constraints: e.g., "FakeEmbeddingProvider only", "No auto-send"]
- [Prior decisions that apply]

Review the following aspects:

### 1. Consistency with Existing Architecture
- Does the proposed design follow the same patterns as existing modules?
- Does it respect the established module boundaries and dependency direction?
- Does it introduce any architectural contradictions?

### 2. Module Boundary and Coupling
- Are the proposed module boundaries clear and well-defined?
- Is there any unnecessary coupling between modules?
- Could the design be simplified by reducing the number of new modules or interfaces?

### 3. Data Flow
- Is the data flow clearly described (input types, processing steps, output types)?
- Are there any missing or ambiguous data transformations?
- Is error handling accounted for in the data flow?

### 4. Design Decisions
- For each key design decision in the design document:
  - Is the rationale sound?
  - Were appropriate alternatives considered?
  - Does the decision align with project constraints?

### 5. Risk Assessment
- What are the architectural risks in this design?
- Are any risks unmitigated or insufficiently addressed?

Provide a structured review with:
- **APPROVED** / **CONDITIONALLY APPROVED** / **CHANGES REQUESTED** status
- Specific findings per aspect
- Action items for any issues found
```

### Expected Output

- A structured review with APPROVED, CONDITIONALLY APPROVED, or CHANGES REQUESTED status
- Findings organized by the five aspects (consistency, boundaries, data flow, decisions, risks)
- Specific, actionable items for any issues
- If CONDITIONALLY APPROVED: clear conditions that must be satisfied before proceeding

### Acceptance Checklist

- [ ] Review covers all five aspects (consistency, boundaries, data flow, decisions, risks)
- [ ] Status is clear and unambiguous
- [ ] Issues are specific and actionable (not vague concerns)
- [ ] Design decisions are evaluated against alternatives, not just accepted
- [ ] Architectural risks are identified and mitigation suggested
- [ ] No claims about capabilities that do not exist

### Common Failure Modes

- **Reviewing implementation instead of architecture**: Focus on module boundaries, interfaces, and data flow, not on how functions are written.
- **Accepting vague descriptions**: "The system processes data" is not architecture. Push for specific data types, transformation steps, and error paths.
- **Missing inconsistency with existing patterns**: A new module that follows completely different patterns than existing ones creates maintenance burden. Consistency matters.
- **Not questioning decisions**: Every "we chose X because..." should be evaluated. Is the rationale sound? Were real alternatives considered?
- **Overlooking error handling**: Architecture reviews that skip error and edge case handling produce fragile designs.

---

## 2. Schema / Data Contract Review

### Purpose

Review data contracts (schemas, models, DTOs) for correctness, completeness, consistency, and forward-compatibility. Data contracts are the backbone of pipeline-based architectures and must be reviewed before implementation.

### When to Use

- When a design document proposes new or modified Pydantic models/schemas
- When a change introduces new data types or modifies existing data contracts
- When reviewing integration points between pipeline stages
- Before implementing serialization or persistence for new data types

### Inputs to Provide

- **Design document**: Where the proposed schemas are described
- **Existing schemas**: Links to current data contract documentation
- **Pipeline context**: How the data flows through the system stages
- **Review focus areas**: Specific concerns (compatibility, serialization, validation)

### Forbidden Scope

- Do NOT review implementation code (focus on schema definitions)
- Do NOT review UI or display logic for schema fields
- Do NOT add fields "for future use" without current requirements
- Do NOT suggest changes that violate established product constraints

### Prompt Template

```
I need you to review the data contracts for this proposed change.

**Change**: [Change name]
**Design document**: [path/to/design.md]

**Existing data contracts**: [Link to current schema documentation]

**Proposed schemas**:
- [Schema name 1]: [Brief description]
- [Schema name 2]: [Brief description]

Review the following aspects:

### 1. Field Completeness
- Are all required fields present for each schema?
- Are there fields that seem unnecessary or unused?
- Are the field types appropriate for their purpose?

### 2. Consistency with Existing Schemas
- Do naming conventions match existing schemas?
- Are field types consistent (e.g., same type for similar fields across schemas)?
- Do existing schemas need modification to accommodate the new contracts?

### 3. Forward Compatibility
- Can new fields be added in the future without breaking existing consumers?
- Are optional fields appropriately marked as optional (with defaults)?
- Is the schema designed to be extended without breaking changes?

### 4. Validation Rules
- Are field validations clearly defined?
- Are there edge cases or boundary conditions that are not validated?
- Are validation errors handled gracefully in the pipeline context?

### 5. Serialization
- Are all fields JSON-serializable (if persistence or API integration is planned)?
- Are custom types properly handled for serialization/deserialization?

Provide a structured review with:
- **APPROVED** / **CHANGES REQUESTED** status
- Specific findings per aspect
- Concrete suggestions for any issues found
```

### Expected Output

- A structured review with APPROVED or CHANGES REQUESTED status
- Findings per aspect (completeness, consistency, compatibility, validation, serialization)
- Concrete field-level suggestions (not vague observations)
- Schema recommendations that balance correctness with simplicity

### Acceptance Checklist

- [ ] All proposed schemas are reviewed for field completeness
- [ ] Naming and type consistency with existing schemas is verified
- [ ] Forward-compatibility concerns are identified
- [ ] Validation rules and edge cases are examined
- [ ] Serialization readiness is evaluated
- [ ] No fields added "just in case" without current requirement

### Common Failure Modes

- **Over-engineering schemas**: Adding fields for hypothetical future use cases adds complexity without value. Review with "do we need this now?" rigor.
- **Inconsistent naming**: Using different naming conventions for new schemas compared to existing ones creates confusion. Enforce consistency.
- **Missing optional field defaults**: Optional fields without defaults break consumers that don't provide them. Recommend sensible defaults.
- **Not considering serialization**: Pydantic models used in memory but expected to be JSON-serializable for persistence need proper configuration. Flag serialization gaps.
- **Ignoring pipeline compatibility**: If a new schema is inserted into an existing pipeline stage, existing downstream consumers must still work. Check forward and backward compatibility.

---

## 3. Integration Boundary Review

### Purpose

Review integration points between modules, pipeline stages, and external services to ensure clean separation of concerns, appropriate abstraction, and safe extensibility.

### When to Use

- When a design introduces a new module that interacts with existing ones
- When adding a new pipeline stage or modifying an existing stage's interface
- When integrating an external service or provider
- When reviewing the dependency direction between modules

### Inputs to Provide

- **Integration design**: How the new module connects to existing modules
- **Pipeline architecture**: Current pipeline stage interfaces and data flow
- **Existing module interfaces**: What the existing modules export and expect
- **Abstraction boundaries**: Where abstraction layers exist or are proposed

### Forbidden Scope

- Do NOT review internal module implementation (focus on integration surface)
- Do NOT propose integration simplifications that break separation of concerns
- Do NOT suggest direct coupling where abstraction is appropriate
- Do NOT recommend adding dependencies on unavailable capabilities

### Prompt Template

```
I need you to review the integration boundaries for this proposed change.

**Change**: [Change name]
**Design document**: [path/to/design.md]

**Existing module interfaces**:
- [Module 1]: [What it exports and expects]
- [Module 2]: [What it exports and expects]

**Proposed integration points**:
- [How the new module connects to Module 1]
- [How the new module connects to Module 2]

Review the following aspects:

### 1. Interface Surface
- Is the proposed interface between modules minimal and focused?
- Does it expose implementation details unnecessarily?
- Could the interface be simplified?

### 2. Dependency Direction
- Does the dependency direction make sense (stable modules depend on more stable ones)?
- Are there any circular dependencies or dependency inversions that need resolution?
- Does the design respect the existing dependency hierarchy?

### 3. Abstraction Layer
- Where abstraction layers exist, do they provide meaningful decoupling?
- Are abstractions motivated by actual variation points (not hypothetical future needs)?
- Is the abstraction boundary well-defined and documented?

### 4. Extensibility Without Modification
- Can new implementations be added without modifying existing integration code?
- Are provider or plugin interfaces designed for open/closed principle?
- Is there a mechanism for selecting between implementations at integration points?

### 5. Error Propagation
- How do errors cross integration boundaries?
- Are integration error types consistent with existing patterns?
- Is there a risk of integration errors causing cascading failures?

Provide a structured review with:
- **APPROVED** / **CHANGES REQUESTED** status
- Specific findings per aspect
- Concrete recommendations for any issues
```

### Expected Output

- A structured review with APPROVED or CHANGES REQUESTED status
- Findings organized by the five aspects (interface surface, dependency direction, abstraction layer, extensibility, error propagation)
- Specific interface or boundary recommendations

### Acceptance Checklist

- [ ] Integration interfaces are evaluated for minimal surface area
- [ ] Dependency direction is verified to be consistent and acyclic
- [ ] Abstractions are justified by actual need (not hypothetical)
- [ ] Extensibility is provided without requiring modification of existing code
- [ ] Error propagation across boundaries is addressed

### Common Failure Modes

- **Leaky abstractions**: An interface that exposes implementation details (e.g., database query params through a retrieval interface). The interface should hide implementation.
- **Over-abstraction**: Creating abstract interfaces for every module "just in case" adds complexity with no current benefit. Abstraction should be motivated by actual variation.
- **Circular dependencies**: Module A imports Module B, and Module B imports Module A. This creates tight coupling and testability issues. Flag immediately.
- **Missing error boundaries**: Errors that propagate unhandled across module boundaries cause unpredictable failures. Each boundary should have defined error handling.
- **Inconsistent integration patterns**: One module uses direct instantiation while another uses dependency injection without clear rationale. Consistency aids maintainability.

---

## 4. Provider Abstraction Review

### Purpose

Review the design of provider/service abstractions to ensure they are appropriately abstracted, substitutable, and safe. This applies to embedding providers, generation providers, or any external service integration.

### When to Use

- When designing or reviewing an abstract provider interface
- When adding a new provider implementation (fake or real)
- When evaluating whether an abstraction is necessary or over-engineered
- When reviewing provider selection logic (fake vs. real)

### Inputs to Provide

- **Provider interface**: The abstract class or protocol definition
- **Existing implementations**: Current fake and real provider implementations
- **Selection mechanism**: How the system chooses which provider to use
- **Provider requirements**: What guarantees each provider must make

### Forbidden Scope

- Do NOT recommend adding real provider implementations without security review
- Do NOT suggest merging fake and real provider implementations into one class
- Do NOT recommend adding provider features not required by current scope
- Do NOT claim real provider capabilities from fake provider implementations

### Prompt Template

```
I need you to review the provider abstraction design for this change.

**Change**: [Change name]
**Design document**: [path/to/design.md]

**Provider interface**: [Abstract class or protocol definition]

**Implementations**:
- [Implementation 1]: [Fake/Real, description]
- [Implementation 2]: [Fake/Real, description]

**Selection mechanism**: [How providers are selected]

Review the following aspects:

### 1. Interface Design
- Is the interface minimal and complete (all necessary methods, nothing extra)?
- Are method signatures stable and unlikely to need frequent changes?
- Is the return type sufficiently rich for all expected implementations?

### 2. Substitutability
- Can a fake provider and a real provider be swapped without changing callers?
- Does the interface allow both deterministic (fake) and non-deterministic (real) behavior?
- Are there any assumptions in the interface that favor one implementation over another?

### 3. Provider Selection Safety
- Is the default provider the fake/safe one?
- Does real provider selection require explicit configuration?
- What happens if a real provider is selected but not configured correctly?
- Is there a graceful fallback to the fake provider on configuration failure?

### 4. Security and Secrets
- Does the provider interface avoid leaking credentials or internal state?
- Are error messages sanitized (no API keys in exception messages)?
- Is there a mechanism for validating required configuration at startup?

### 5. Testing Implications
- Can tests use the fake provider without external dependencies?
- Is the fake provider deterministic for reproducible tests?
- Does the interface design allow for easy mocking in unit tests?

Provide a structured review with:
- **APPROVED** / **CHANGES REQUESTED** status
- Specific findings per aspect
- Concrete suggestions for improvement
```

### Expected Output

- A structured review with APPROVED or CHANGES REQUESTED status
- Findings per aspect (interface design, substitutability, selection safety, security, testing)
- Specific interface or implementation recommendations
- Security notes on provider credential handling

### Acceptance Checklist

- [ ] Provider interface is minimal and complete
- [ ] Fake and real implementations are truly substitutable
- [ ] Default provider is the safe/fake one (not real)
- [ ] Real provider requires explicit configuration
- [ ] Graceful fallback exists on configuration failure
- [ ] No credentials leaked through the interface or error messages
- [ ] Fake provider is deterministic for testing

### Common Failure Modes

- **Interface too narrow**: The abstract interface doesn't support all features a real provider would need, requiring interface changes later.
- **Interface too broad**: Including methods that only one implementation needs. Push specialization into the implementation, not the interface.
- **Fake provider not deterministic**: A fake provider that uses randomness or external state cannot be used for reproducible tests. Require determinism.
- **Defaulting to real provider**: If real provider is the default and requires no configuration, it will crash on first use when credentials are missing. Default to fake.
- **Leaky credentials**: Error messages from real provider failures may include API keys or tokens. Sanitize at the abstraction boundary.

---

## 5. Optional Workflow Design

### Purpose

Review the design of optional or additive workflows that extend a core pipeline without modifying it. This pattern is used when new functionality should be available but not forced on existing consumers.

### When to Use

- When a change proposes an optional stage or workflow layered on top of an existing pipeline
- When new functionality must coexist with an existing pipeline contract
- When deciding between modifying a core function vs. creating a wrapper function
- When designing entrypoints that compose existing capabilities

### Inputs to Provide

- **Core pipeline interface**: The existing function or module that must not change
- **Optional workflow design**: How the new functionality composes with the existing one
- **Wrapper or entrypoint design**: The new function(s) that combine core + optional functionality
- **Consumer impact analysis**: What changes, if any, existing callers must make

### Forbidden Scope

- Do NOT modify the core pipeline return type or signature to accommodate optional functionality
- Do NOT suggest breaking changes to existing consumers
- Do NOT recommend wrapping the core pipeline in a way that hides its contract
- Do NOT add conditional branches inside the core pipeline to support optional features

### Prompt Template

```
I need you to review the optional workflow design for this change.

**Change**: [Change name]
**Design document**: [path/to/design.md]

**Core pipeline interface** (must NOT change):
[Function signature and return type]

**Optional workflow proposal**:
[How the new functionality layers on top of the core pipeline]

**Proposed entrypoints**:
- [Entrypoint 1]: [Description]
- [Entrypoint 2]: [Description]

**Existing consumers**:
- [Consumer 1]: [How it uses the core pipeline]
- [Consumer 2]: [How it uses the core pipeline]

Review the following aspects:

### 1. Core Pipeline Integrity
- Does the optional workflow modify the core pipeline in any way?
- Are the return types of core functions unchanged?
- Can existing consumers continue using the core pipeline without any code changes?

### 2. Optional Entrypoint Design
- Is the wrapper/entrypoint function clearly distinct from the core pipeline?
- Does it compose the core pipeline without modifying intermediate state?
- Is the entrypoint naming clear about what it adds beyond the core pipeline?

### 3. Consumer Choice
- Can consumers opt in to the optional workflow without breaking changes?
- Is the optional workflow discoverable but not accidentally invoked?
- Are there any implicit dependencies the optional workflow creates?

### 4. Return Type Design
- If a new return type wraps the core output, is it narrow and focused?
- Does it avoid duplicating or abstracting the core type unnecessarily?
- Can consumers access core output without unwrapping complex nested types?

### 5. Maintenance Burden
- Does the optional workflow create parallel code paths that must be kept in sync?
- What is the testing burden for maintaining both core and optional paths?
- Are there patterns that could simplify maintenance (shared logic, base classes)?

Provide a structured review with:
- **APPROVED** / **CHANGES REQUESTED** status
- Specific findings per aspect
- Concrete suggestions
```

### Expected Output

- A structured review with APPROVED or CHANGES REQUESTED status
- Findings per aspect (core integrity, entrypoint design, consumer choice, return type, maintenance)
- Specific design recommendations for the wrapper architecture
- Consumer migration guidance if applicable

### Acceptance Checklist

- [ ] Core pipeline is NOT modified
- [ ] Existing consumers require NO changes
- [ ] Optional entrypoint is clearly distinguished from core pipeline
- [ ] Return type is narrow and does not abstract the core type
- [ ] No implied dependencies from optional workflow
- [ ] Testing burden is documented and acceptable

### Common Failure Modes

- **Core pipeline modification**: Adding a parameter, changing return type, or adding conditional branches to the core pipeline to support optional features. This breaks the contract.
- **Wrapper hides the core**: A wrapper that returns an opaque type hiding the core output forces consumers who need the core output to unwrap it. Keep types transparent.
- **Accidental invocation**: If the optional workflow is triggered by default or has side effects on import, consumers get behavior they didn't ask for. Require explicit opt-in.
- **Parallel code divergence**: The core pipeline and the optional workflow share logic but are maintained separately. Extract shared logic to avoid divergence.
- **Testing blind spot**: Testing only the optional workflow and assuming the core pipeline still works creates regression risk. Test both paths independently.

---

## Prompt Index

| Prompt | Purpose | When to Use |
|--------|---------|-------------|
| Architecture Review | Evaluate overall architecture soundness and consistency | Design document review |
| Schema / Data Contract Review | Review proposed data models and contracts | Schema design phase |
| Integration Boundary Review | Review module integration surfaces | New module, pipeline stage, or external service |
| Provider Abstraction Review | Review abstract provider interface and implementation | Provider design or new implementation |
| Optional Workflow Design | Review additive workflow that extends core pipeline | Optional stage or wrapper entrypoint design |
