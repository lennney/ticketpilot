# Proposal: Evidence-Grounded LLM Draft Generation (Phase 11)

## Executive Summary

Phase 10 confirmed that retrieval evidence quality is sufficient (Doc-ID Recall@10: 91.9%, 78% of wrong cases reclassified as metric granularity). The remaining product gap is not retrieval quality but **draft generation**: retrieved evidence exists but is still assembled via simple templates (FakeDraftProvider). Moving from template-based drafting to LLM-based evidence-grounded drafting is the next portfolio frontier.

Phase 11 introduces an LLM draft generation layer that consumes retrieved evidence candidates and produces structured, citation-enforced draft replies. The LLM is constrained to generate only from retrieved evidence — it must not decide policy, risk, compensation, legal interpretation, or account-security actions by itself. All high-risk, insufficient-evidence, and unsupported-claim outputs route to human review.

**No retrieval algorithm changes. No RRF tuning. No embedding changes. No knowledge expansion. No golden label changes. No auto-send.**

## Baseline (Current State after Phase 10)

### Retrieval Quality (Phase 10 confirmed)
| Metric | Value |
|---|---|
| Doc-ID Recall@10 | 91.9% |
| Doc-type Recall@10 | 59.4% |
| Wrong cases reclassified as doc-ID found | 32/41 (78%) |
| Zero-hit cases (query expansion candidates) | 7 |
| Partial-hit cases (fusion ranking candidates) | 32 |

### Current Draft Generation
- **FakeDraftProvider**: deterministic template-based drafting — no LLM, no semantic understanding
- **Citations**: present in DraftReply schema, generated deterministically from top-3 evidence
- **Unsupported-claim guard**: CitationValidator checks `[N]` markers and evidence cross-references
- **Fallback**: hardcoded `NO_EVIDENCE_FALLBACK_TEXT` when no evidence candidates
- **No draft quality metrics**: evaluation covers classification, risk, and evidence recall but not draft quality

## Problem

1. **Template-based drafts are not portfolio-grade.** FakeDraftProvider generates simple single-sentence templates that demonstrate pipeline connectivity but not realistic draft quality. The portfolio story cannot credibly claim "evidence-grounded drafting" without an actual generation engine.

2. **LLM integration is the natural next capability.** The project has: evidence retrieval (Phase 8), evaluation (Phase 7), ranking diagnosis (Phase 10). The next portfolio dimension is draft generation with guardrails.

3. **Guardrails must be designed before the LLM is integrated.** Unconstrained LLM draft generation risks: hallucinated policy commitments, unauthorized refund/compensation promises, ignored risk signals, bypassed human review. The guard architecture must be designed as part of the generation system, not retrofitted.

4. **No existing draft evaluation.** Current evaluation measures accuracy/recall for classification, risk, and evidence — but not whether the generated draft is factually grounded in evidence.

## Goal

1. **LLM provider abstraction**: Define an `LLMProvider` interface with a deterministic fake provider for tests and the architecture for an OpenAI-compatible real provider (implementation deferred).

2. **Evidence-grounded draft generation**: LLM generates draft replies from retrieved evidence candidates only. Every factual/policy statement must cite evidence.

3. **Citation-enforced output**: Generated drafts include structured citations mapping statements to evidence chunk_ids.

4. **Unsupported-claim guard**: Post-generation guard detects:
   - Claims made without supporting citations
   - Forbidden promises (refund amounts, compensation, legal guarantees, account actions)
   - Statements contradicting or exceeding retrieved evidence

5. **Human review handoff**: Drafts with guard failures, high-risk flags, or insufficient evidence route to human review. No auto-send.

6. **Draft evaluation**: Offline metrics for citation precision, evidence coverage, unsupported-claim rate, safe fallback rate, and human-review trigger correctness.

7. **Portfolio-grade demo**: The three existing demo scenarios (退款投诉, 隐私/账号异常, 发票/支付争议) produce evidence-grounded drafts visible in the human review console.

## Non-Goals

- Not building a production-ready system
- Not using real enterprise customer data
- Not running online A/B tests
- Not auto-sending customer replies
- Not replacing human agents with AI
- Not tuning retrieval algorithm, RRF, or embeddings
- Not adding knowledge records
- Not changing golden labels
- Not implementing the real LLM provider (phase 11.3+; API key config deferred)
- Not making legal, refund, compensation, or account-security decisions by LLM
- Not restructuring the pipeline architecture
- Not modifying Phase 7/8/9/10 baseline reports
- Not calling any external LLM API during this planning phase

## Scope

### In Scope
- LLM provider abstraction (interface + deterministic fake provider)
- Evidence-grounded prompt builder (constrain LLM to retrieved evidence)
- Structured draft output with citations
- Claim guard validator (evidence coverage, citation existence, forbidden promise detection)
- Human review console updates (guard results visible, review triggers documented)
- Offline draft evaluation metrics
- Three demo scenario draft evaluation

### Out of Scope
- Real LLM provider implementation (API integration deferred to later sub-phase)
- Retrieval algorithm changes
- RRF parameter tuning
- Query expansion changes
- Knowledge base expansion
- Embedding provider changes
- Golden label changes
- Archived report modifications
- Multi-agent orchestration

## Success Criteria

1. LLM provider interface defined with fake deterministic provider working
2. Evidence-grounded prompt builder produces constrained prompts from evidence candidates
3. Structured draft output includes citations and guard results
4. Claim guard detects: uncited claims, forbidden promises, insufficient-evidence drafts
5. Guard failures correctly flag `must_human_review=True`
6. Human review console displays draft, evidence, guard results, and risk flags
7. Offline draft evaluation computes citation precision, evidence coverage, unsupported-claim rate
8. No Phase 7/8/9/10 reports modified
9. No retrieval algorithm changed
10. OpenSpec scoped validation passes
11. Full quality gate required for pipeline/code changes; 0 skipped integrations

## Risks

| Risk | Mitigation |
|---|---|
| LLM hallucinates policy despite constraints | Citation-enforced generation + post-generation claim guard; both must pass for auto-approve |
| LLM provider integration couples to specific API | Abstract provider interface; fake provider for CI; real provider opt-in via .env.local |
| Draft quality metrics may be low with fake provider | Fake provider is for pipeline verification only; real provider evaluation deferred |
| Guard false positives block legitimate drafts | Guards flag for human review, do not block; reviewer can override |
| Scope creep into retrieval or knowledge work | Explicit out-of-scope list; stop conditions in every batch |

## Validation Plan

| Stage | Validation | Notes |
|---|---|---|
| Planning (current batch) | `openspec validate add-evidence-grounded-llm-draft --strict` | Scoped |
| Implementation batches | Module-level tests for each component | Per tasks.md |
| Pre-archive | Full quality gate + integration 0 skip | Core pipeline changes |
