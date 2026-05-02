# Evaluation Plan

> **Status note (2026-05-02):** This document describes an aspirational evaluation
> framework. No evaluation scripts, test sets, or golden answer data have been
> implemented. The evaluation pipeline is a deferred item. See `docs/phase_status.md`
> for current implementation state.

TicketPilot evaluation is divided into five layers:

1. Classification evaluation
- Accuracy
- Macro-F1

2. Retrieval evaluation
- Recall@3
- Recall@5
- MRR

3. Evidence evaluation
- Citation correctness
- Evidence support rate

4. Risk gate evaluation
- High-risk recall
- False blocking rate

5. Human review evaluation
- Draft acceptance rate
- Human edit rate
- Escalation correctness

The first evaluation implementation should use self-built scripts before adding heavier evaluation tooling.
