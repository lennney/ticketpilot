# Phase 12 Data Story for Interviews

**Scope**: Local demo / portfolio prototype — for AI PM / AI engineer / RAG engineer / QA engineer interviews
**Generated**: 2026-05-07
**Key numbers**: 101 synthetic tickets, 106 knowledge records, Doc-ID Recall@10 = 91.9%, Phase 12 provider comparison (25 cases, fake + real), strict quality gate (1069 unit + 146 integration tests, 87% coverage)

---

## 30-Second Data Story

> "TicketPilot is a Chinese customer service ticket triage copilot I built through 6 iterative phases. It processes unstructured tickets through intent classification, risk assessment, hybrid knowledge retrieval (keyword + vector + RRF fusion), and evidence-grounded draft generation — all with a mandatory human review layer before any action. The system is offline-evaluated on 101 synthetic tickets with a 106-record knowledge base. Retrieval achieves Doc-ID Recall@10 of 91.9% after diagnosis and metric correction. A Phase 12 comparison validated that both a fake template-based provider and a real DeepSeek provider produce identical human review trigger patterns on 25 fixture cases. The project is fully tested: 1069 unit tests, 146 integration tests, 87% coverage, and an OpenSpec-validated spec tree."

---

## 1-Minute Data Story

> "TicketPilot is a Chinese customer service ticket triage system that processes free-text tickets through a six-stage pipeline: intake normalization, intent classification across 8 categories, risk assessment with 8 flag types, hybrid retrieval using FTS + pgvector HNSW + RRF fusion, evidence-grounded draft generation, and human review. Every decision is recorded in an append-only JSONL audit trail.
>
> The project went through 6 phases. Phase 7 built the evaluation foundation — 101 synthetic tickets and 106 knowledge records. Phase 8 compared fake vs real embeddings — discovered the real bottleneck was knowledge coverage, not embedding quality. Phase 9 added 11 knowledge records based on evaluation gaps, built a Provider Identity Gate. Phase 10 diagnosed retrieval: found that 78% of 'wrong' cases were metric granularity issues — doc-type showed 59.4% recall, but doc-id showed 91.9% after correction. Phase 11 added evidence-grounded LLM draft generation with 8 safety layers including CitationValidator and ClaimGuard. Phase 12 ran an offline provider comparison: both fake and real (DeepSeek) providers succeeded on all 25 cases with identical human review triggers — confirming the safety rules are provider-agnostic.
>
> The quality gate is strict: 1069 unit tests, 146 integration tests, 87% coverage, OpenSpec-validated. This is a local demo — not production, not real customer data."

---

## 3-Minute Technical Walkthrough

### Architecture

> "TicketPilot uses a stage-based modular pipeline in Python. Each stage has try/except graceful degradation — a failure produces fallback values and continues. The system is deterministic by default (fake embeddings, fake LLM), with real providers opt-in via environment variables. Safety is architectural: no auto-send, human review mandatory for HIGH risk."

### Phase 7: Evaluation Foundation

> "Phase 7 built the evaluation infrastructure from scratch. Created 101 synthetic tickets covering 8 intent categories and 8 risk types. Created 106 knowledge records (FAQ/Policy/Case). Built an offline evaluation CLI that runs the full pipeline and computes metrics against golden labels. The insight was: you can't improve what you can't measure."

### Phase 8: Real Retrieval Upgrade

> "Phase 8 compared fake vs real embeddings. The fake provider uses deterministic 384-d hash vectors — useful for pipeline verification but semantically meaningless. The real provider uses DashScope text-embedding-v4 (1024-d Chinese-optimized). The comparison revealed the real bottleneck was not the embedding model but knowledge coverage — the knowledge base was missing records that matched evaluation queries."

### Phase 9: Evaluation-Driven Knowledge Optimization

> "Phase 9 added 11 records to the knowledge base based on evaluation gap analysis. Also discovered a silent config fallback bug: when the embedding provider wasn't configured, it fell back to fake without logging a warning. Built a Provider Identity Gate to make provider configuration explicit."

### Phase 10: Retrieval Diagnosis

> "Phase 10 was the most interesting phase from an evaluation perspective. I noticed the doc-type Recall@10 was only 59.4%, but the metric felt wrong. When I added doc-level labels — marking which specific chunk ID should be retrieved for each case — the doc-ID Recall@10 jumped to 91.9%. The gap was explained by metric granularity: 32 out of 41 'wrong' cases had the right document in the top-10, but the doc-type metric was counting the case as wrong because not all chunks were retrieved. This is a classic measurement vs. reality problem in RAG evaluation."

### Phase 11: Draft Generation

> "Phase 11 added evidence-grounded LLM draft generation with 8 safety layers. The prompt builder assembles evidence blocks and safety instructions. The CitationValidator checks that cited evidence IDs actually exist. The ClaimGuard checks for forbidden promises (e.g., '一定退款') and unsupported claims. HIGH risk triggers mandatory human review. This is the part I'm most proud of — the safety architecture is layered and explicit."

### Phase 12: Provider Comparison

> "Phase 12 validated that the draft generation pipeline works with both a fake template provider and a real OpenAI-compatible provider (DeepSeek). Both succeeded on all 25 cases with identical human review triggers — suggesting the safety rules are wired correctly regardless of the LLM. The quality gate is strict: 1069 unit tests, 146 integration tests, 87% coverage."

---

## Product Manager Version

> "TicketPilot is a customer service ticket triage copilot that prioritizes human oversight over automation. The key design decision was: high-risk tickets (legal threats, account security, compensation demands) always require human review — the system generates a citation-grounded draft, but a human makes the final call. This is not an auto-reply system. The project demonstrates a measurement-first approach: each phase used evaluation data to identify the next bottleneck, rather than adding features blindly. The result is a system with known boundaries, explicit safety layers, and a full audit trail."

---

## AI Application / Agent Workflow Version

> "TicketPilot is an agent workflow for customer service triage. The agent reads unstructured Chinese tickets, classifies intent (8 types), assesses risk (8 flags), retrieves relevant policy/FAQ/case documents, generates an evidence-grounded draft reply, and routes high-risk outputs to a human reviewer. The workflow is deterministic by default — no real LLM required — which makes it fully testable. The Phase 12 comparison validates that switching from a template-based generator to a real LLM doesn't break the safety constraints: human review triggers are identical across both."

---

## RAG Engineering Version

> "TicketPilot implements hybrid retrieval: PostgreSQL FTS for keyword matching, pgvector HNSW (m=16, ef_construction=200) for vector similarity, and Reciprocal Rank Fusion (RRF, k=60) to combine both signals. The evaluation story is the key technical lesson: doc-type level metrics (59.4% recall) masked the real performance. When we switched to doc-ID level metrics with per-case golden labels, we found 91.9% recall. The lesson: in RAG evaluation, the granularity of your metric must match the granularity of your question. Doc-type evaluation conflates chunk retrieval with document relevance."

---

## Quality Engineering Version

> "TicketPilot has a strict quality gate: 1069 unit tests, 146 integration tests, 87% code coverage, ruff linting, and OpenSpec spec validation (22 specs). The gate runs on every batch and is non-negotiable — no `|| true` bypasses, no skipped integration tests allowed for archive/push. The Phase 12C.2 incident illustrated why: we temporarily weakened the gate to speed up iteration, and the weakened state got committed. The fix was to restore strict isolation — running tests with `TICKETPILOT_LLM_PROVIDER=fake` to prevent local environment interference. The gate now enforces zero compromises."

---

## Do Not Say

- ~~"Production-ready"~~
- ~~"Real enterprise validated"~~
- ~~"Real customer data"~~
- ~~"Real-world benchmark"~~
- ~~"Auto-send"~~
- ~~"Replaces human agents"~~
- ~~"Guaranteed accuracy"~~
- ~~"Works at scale"~~

## Must Always Say

- "Local demo / portfolio prototype"
- "Synthetic/adapted data"
- "Offline evaluation only"
- "Offline fixture-based comparison"
- "Draft-only"
- "No auto-send"
- "Human-in-the-loop"
- "No real customer data"
- "Not production-ready"
- "Not real enterprise validated"
- "Not a real-world benchmark"
