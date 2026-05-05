# Phase 9 — Evaluation-Driven Knowledge Coverage Optimization

## One-Sentence Summary

Phase 9 built an evaluation-driven loop to identify knowledge gaps, add targeted
synthetic records, and measure retrieval impact — uncovering that fake embeddings
can be directionally misleading, and that under real semantic retrieval, knowledge
expansion shows measurable but incomplete improvement.

## Iteration Chain

| Phase | What | Key Output |
|-------|------|-----------|
| 9.2 | Wrong-case taxonomy | 41 wrong cases → 8 failure categories |
| 9.3 | Knowledge gap mapping | 24 gap IDs across FAQ/Policy/Case, 30 knowledge-addressable |
| 9.4 | Targeted P0 expansion | 11 synthetic records (1 FAQ + 4 Policy + 6 Case) |
| 9.5 | Fake evaluation rerun | Fake: Top-1 -5.0%, 0 wrong cases fixed — inconclusive |
| 9.5.1 | Validation repair + P0 audit | Fake P0 hit rate: 3/16 (18.8%), 0 fixes |
| 9.5.3 | `.env.local` fix + real rerun | Real P0 hit rate: 12/16 (75.0%), Top-1 +2.0% |

The arc: taxonomy → gaps → records → fake eval (misleading) → root cause fix → real eval (valid).

## Key Metrics

| Metric | Phase 8 Real (95) | Phase 9 Real (106) | Delta |
|--------|-------------------|--------------------|-------|
| Knowledge records | 95 | 106 | +11 |
| Top-1 hit rate | 42.6% | 44.6% | +2.0% |
| Top-3 hit rate | 56.4% | 54.5% | -2.0% |
| Top-10 hit rate | 59.4% | 59.4% | 0.0% |
| MRR (doc_type) | 0.4913 | 0.4995 | +0.0082 |
| Wrong cases | 41 | 41 | 0 |
| P0 added-record hit rate | — | 12/16 (75.0%) | — |

## Key Findings

### 1. Fake evaluation can be directionally misleading

Under fake embeddings, Phase 9 knowledge expansion appeared to **regress** Top-1 by 5.0%.
Under real embeddings, the same expansion **improved** Top-1 by 2.0%. The fake provider's
deterministic random vectors created noise that overwhelmed the signal. This finding
informs the **Provider Identity Gate** (`docs/technical/provider_identity_gate.md`).

### 2. Real embedding shows measurable effect of knowledge expansion

P0 hit rate jumped from 18.8% (fake) to 75.0% (real) — a 4× improvement. Under real
semantic embeddings, 12 of 16 new records surfaced in the top-10 for their intended
queries, with P0 Policy records reaching as high as rank 1 for their target cases.

### 3. Wrong cases unchanged means the next bottleneck is not simply knowledge coverage

Despite 75% P0 hit rate and +2.0% Top-1 improvement, wrong cases stayed at 41.
Most P0-targeted cases (12/14) were already passing under Phase 8 real — the required
doc types were already present. The remaining 2 wrong cases miss Policy doc type,
and P0 Policy records didn't displace the existing top-10 entries.

The bottleneck has shifted from **knowledge coverage** to **retrieval ranking**:
relevant documents exist but don't rank high enough to displace irrelevant ones of
the right type.

### 4. `.env.local` loading bug was a systemic blind spot

`python-dotenv` was in `pyproject.toml` but never called. All `EMBEDDING_*` vars from
`.env.local` were invisible to `os.environ`, causing silent fallback to `fake` provider.
This went undetected across multiple Phase 9 evaluation runs. The fix is a one-line
`load_dotenv()` call, plus a `__repr__` that redacts `api_key`, plus 10 unit tests.

## Product Manager Perspective

This phase is not about "blindly swapping models" or "blindly adding knowledge."
It is about building the evaluation infrastructure to know **which** bottleneck
matters next:

- **Provider Identity Gate:** Don't trust your own metrics until you verify what
  provider actually generated them.
- **Added-Record Hit Audit:** Don't just count wrong cases — check whether new
  records actually surface for their intended queries.
- **Real-Provider Evaluation Gate:** Don't claim semantic improvement from fake
  embeddings.

The narrative: *We added 11 targeted knowledge records based on a systematic gap
analysis of 41 wrong cases. Initially, fake embeddings showed regression. After
fixing a config loading bug, real embeddings showed improvement, and 75% of new
records surfaced for their intended queries. Wrong cases didn't decrease — meaning
the next problem is retrieval ranking, not knowledge coverage. We now have the
evaluation infrastructure to measure that next step.*

## Project Boundaries

This is a **local demo / portfolio prototype** with the following constraints:

- **Synthetic/adapted data only** — no real customer data, no raw scraping
- **Offline evaluation** — retrieval comparison against golden expectations, no online A/B testing
- **Draft-only** — the pipeline generates draft replies; all decisions are advisory
- **Human-in-the-loop** — HIGH risk or low confidence cases require human review
- **Not a production benchmark** — metrics are directional, not SOTA comparisons
- **Single developer** — all infrastructure, evaluation, and reporting built by one person

## Resume Bullet

> Built an evaluation-driven knowledge optimization pipeline for an AI customer service
> system. Created a wrong-case taxonomy (41 cases → 8 categories), mapped 24 knowledge
> gaps, added 11 targeted synthetic records, and measured impact with real semantic
> embeddings (dashscope text-embedding-v4). Uncovered a provider identity bug where
> fake embeddings directionally misled Top-1 by 7pp, fixed the config loading, and
> achieved 75% new-record hit rate under real retrieval. Wrong cases remained at 41,
> shifting the bottleneck from knowledge coverage to retrieval ranking — informing
> the next engineering priority.

## Interview Versions

### 1-Minute Version

"Phase 9 was about evaluation-driven knowledge optimization. I started by
categorizing 41 retrieval failures into 8 root cause types, then mapped those to
24 specific knowledge gaps. I added 11 synthetic records targeting the highest-impact
gaps — things like refund escalation policies and counterfeit goods cases.

The interesting part was that when I ran the evaluation with fake embeddings, it
showed a regression. After investigating, I found that `python-dotenv` was installed
but never called — `.env.local` config was silently ignored, and the system had
been falling back to fake embeddings for all Phase 9 runs.

After fixing that and rerunning with real dashscope embeddings, the results flipped:
Top-1 improved 2%, and 75% of new records hit their target queries. But wrong cases
stayed at 41 — which told me the bottleneck had shifted from knowledge coverage to
retrieval ranking. That's now the next engineering priority."

### 3-Minute Version

"Phase 9 is the most interesting phase in TicketPilot so far because it's where
evaluation infrastructure met a real debugging story.

I started with a systematic gap analysis: 41 wrong cases from the Phase 8 retrieval
evaluation. I categorized them into 8 failure modes — things like 'missing Policy
for refund escalation' and 'business domain gap for counterfeit goods.' From that,
I built a 24-entry gap map, separating knowledge-addressable gaps from non-knowledge
issues like query expansion and golden label gaps.

Then I added 11 synthetic records — one FAQ, four policies, and six case precedents —
targeting specific wrong cases. All synthetic, no real customer data. The records
follow the existing schema with proper UUIDs, business domains, and risk levels.

Here's where it gets interesting. When I first ran the Phase 9 evaluation, the
metrics looked bad — Top-1 down 5%. It took digging into the retrieval traces to
realize something was wrong: the `embedding_provider` field said `fake`, even though
I had dashscope API keys in `.env.local.` The root cause was that `python-dotenv`
was a dependency but nobody called `load_dotenv()`. The config module read directly
from `os.environ`, which never saw `.env.local` values.

After fixing that one line and adding proper tests — including API key leak prevention
in `__repr__` — I reran with real `text-embedding-v4` embeddings. The results
reversed: Top-1 up 2%, 75% of new records hitting their target queries. But wrong
cases didn't decrease — 41 before and after.

That negative result is actually the most valuable finding. It means the bottleneck
has shifted. It's no longer 'do we have the right documents?' — it's 'do the right
documents rank high enough?' The next step is retrieval ranking optimization: RRF
fusion weights, query expansion, or hybrid search tuning.

The meta-lesson is about evaluation infrastructure. Without the provider identity
gate I built during this phase, I would have shipped metrics that were directionally
wrong. The evaluation pipeline itself needed evaluation."

## Files Reference

| File | Purpose |
|------|---------|
| `docs/technical/provider_identity_gate.md` | Provider audit and config safety rules |
| `docs/technical/evaluation_mechanism_phase9.md` | Three evaluation modes, hit audit, three-layer diagnosis |
| `reports/retrieval/phase9_wrong_case_taxonomy.md` | 41 cases → 8 failure categories |
| `reports/retrieval/phase9_knowledge_gap_map.md` | 24 gap IDs mapped to wrong cases |
| `reports/retrieval/phase9_p0_knowledge_expansion_summary.md` | P0 record traceability |
| `reports/retrieval/phase9_provider_identity_audit.md` | Provider identity verification |
| `reports/retrieval/phase9_real_rerun.md` | Real provider evaluation results |
| `reports/retrieval/phase9_p0_added_record_hit_audit.md` | Fake provider P0 hit audit (3/16) |
