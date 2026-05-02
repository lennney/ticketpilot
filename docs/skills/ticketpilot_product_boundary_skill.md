# TicketPilot Product Boundary Skill

## Purpose

Define and enforce what TicketPilot IS and what it IS NOT. TicketPilot is a Chinese customer support ticket triage and evidence-grounded reply Copilot, not a generic chatbot, not a generic RAG demo, and not an auto-send tool. This skill prevents scope creep and maintains the product's focused identity during development.

## When to Use

- Evaluating a new feature request or change proposal
- Deciding whether a change belongs in TicketPilot or should be a separate project
- Reviewing design documents for scope compliance
- Onboarding new contributors to the project
- Responding to "why doesn't TicketPilot do X?" questions

## Required Inputs

- Feature or change proposal description
- Understanding of TicketPilot's current architecture: 4-stage pipeline (intake, classification, risk assessment, retrieval) + optional stages (draft generation, human review)
- Current limitations document (docs/portfolio/limitations_and_next_steps.md)
- System architecture reference (docs/technical/system_architecture.md)

## Allowed Scope

- Chinese customer support ticket triage
- Rule-based intent classification (8 classes)
- Deterministic risk assessment (8 flags)
- Hybrid keyword + vector retrieval with PostgreSQL/pgvector
- Optional evidence-grounded draft generation (template-based FakeDraftProvider, no LLM)
- Human review console with Approve/Edit/Escalate/Reject actions and append-only JSONL audit trail
- Local demo and MVP readiness
- Documentation of deferred items, limitations, and future roadmap

## Forbidden Scope

- Do NOT make TicketPilot a generic chatbot (it processes support tickets with structured pipeline stages, not open-ended conversation)
- Do NOT make TicketPilot a generic RAG demo (it targets Chinese customer support knowledge: FAQ, Policy, Case -- not arbitrary document collections)
- Do NOT add auto-send functionality (human review is required by design before any reply dispatch)
- Do NOT add real LLM provider integration without explicit design review (FakeDraftProvider is the only MVP implementation)
- Do NOT add real embedding provider without evaluation pipeline readiness
- Do NOT add multi-language support beyond Chinese
- Do NOT add authentication, multi-user review, or production deployment without a dedicated change
- Do NOT add a generic chatbot conversation endpoint
- Do NOT claim production readiness, real semantic retrieval quality, or real enterprise data coverage

## Step-by-Step Procedure

1. **Identify the proposed feature**
   - What does it do? What problem does it solve? Who is the user?
   - Document the proposal clearly in one paragraph

2. **Check against the "What TicketPilot Does" list**
   - Does the feature fit within: ticket triage, intent classification, risk assessment, knowledge retrieval, draft generation, or human review?
   - If yes: proceed to scope evaluation
   - If no: the feature is likely out of scope for TicketPilot

3. **Check against the "What TicketPilot Does NOT Do" list**
   - Does the feature risk turning TicketPilot into a generic chatbot? (open-ended conversation, no pipeline stages)
   - Does the feature risk turning TicketPilot into a generic RAG demo? (arbitrary document types, no ticket focus)
   - Does the feature add auto-send capability? (dispatching replies without human approval)
   - Does the feature require real LLM or embedding providers without evaluation readiness?
   - If yes to any: the feature is out of scope for the current MVP phase

4. **Apply the three boundary tests**

   **Generic chatbot test**: "Does the feature allow users to have an open-ended conversation with the system?" If yes, reject. TicketPilot processes tickets through a fixed pipeline; it does not chat.

   **Generic RAG demo test**: "Does the feature allow querying arbitrary documents outside FAQ/Policy/Case?" If yes, reject. TicketPilot's knowledge base is specifically Chinese customer support knowledge.

   **Auto-send test**: "Does the feature dispatch replies or trigger external actions without human review?" If yes, reject. Human review is architected as a mandatory gate before any downstream action.

5. **Document the scope decision**
   - If approved: add to the change's design.md with explicit boundary justification
   - If rejected: document why in the proposal or discussion, referencing the product boundary

## Acceptance Checklist

- [ ] Feature fits within the ticket triage and evidence-grounded reply Copilot definition
- [ ] Feature does not create generic chatbot capabilities
- [ ] Feature does not create generic RAG capabilities
- [ ] Feature does not add auto-send or bypass human review
- [ ] Feature does not require real LLM/embedding providers beyond the current MVP state
- [ ] Feature does not make unsubstantiated claims about production readiness, retrieval quality, or data coverage
- [ ] Scope decision is documented in design.md or the proposal discussion

## Common Failure Modes

- **"It's just a small endpoint"**: Adding a generic chat endpoint alongside the pipeline may seem harmless, but it creates an undocumented pathway that bypasses risk assessment, evidence grounding, and human review. This is an architectural boundary violation.
- **"It's just RAG -- we can demo it with any documents"**: TicketPilot's chunking, retrieval, and citation validation are designed for FAQ/Policy/Case knowledge. Using it with arbitrary documents without validating the approach risks incorrect results and misrepresentation.
- **"Approval is basically sending"**: If the reviewer clicks "approve," the system should not auto-send. Approval is a decision-recording action only. The gap between approval and actual dispatch is deliberate and requires explicit integration work.
- **"We can add it later" (scope creep)**: Every new feature should be evaluated against the product boundary at proposal time, not after implementation. Re-scoping after implementation is expensive.
- **Claiming more than is delivered**: Saying "the system generates drafts" is accurate. Saying "the system has an LLM-powered drafting engine" is not. Use precise, verifiable language.

## Reusable Claude Code Prompt Template

```
Evaluate this proposed feature for TicketPilot:

[Feature description]

Apply the three boundary tests:

1. **Generic chatbot test**: Does this allow open-ended conversation? If yes, reject.
2. **Generic RAG demo test**: Does this allow arbitrary document querying outside FAQ/Policy/Case? If yes, reject.
3. **Auto-send test**: Does this dispatch replies or trigger actions without human review? If yes, reject.

Then check:
- Does it fit within: ticket triage, intent classification (8 classes), risk assessment (8 flags), hybrid retrieval (keyword + vector), draft generation (templated, no LLM), or human review (Approve/Edit/Escalate/Reject)?
- Does it require real LLM/embedding providers (not available in MVP)?
- Does it make claims that exceed documented capabilities?

Provide a clear IN SCOPE / OUT OF SCOPE decision with rationale.
```

## TicketPilot Example

**In-scope decision**: The Streamlit human review console (Stage 1D) was evaluated as clearly in scope:
- It supports the ticket triage workflow (review pipeline output, record decisions)
- It does not create a generic chatbot (no conversation endpoint)
- It does not create a generic RAG demo (works with TicketPilot's specific pipeline output)
- It does not add auto-send (all four actions only record decisions to JSONL)
- It does not require real LLM/embedding providers

**Out-of-scope decision**: A proposal to add a generic "ask a question about your data" endpoint was rejected:
- It would allow open-ended conversation (fails generic chatbot test)
- It would allow querying any document (fails generic RAG demo test)
- It would bypass the risk assessment pipeline
- It would require a real LLM provider not available in the MVP

**Out-of-scope decision**: Adding auto-send functionality ("send approved drafts to the customer automatically") was explicitly deferred:
- Human review is a safety gate by design
- Integration with customer service platforms is a separate, future integration change
- The system records decisions; reply dispatch requires platform-specific implementation
