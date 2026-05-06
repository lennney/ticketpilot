# Architecture Decision Log — TicketPilot

*Tracks architecture-level decisions, rationale, and alternatives considered.*

---

## AD-2026-05-06: Phase 10 Evidence Chain Complete — No Further Retrieval Tuning

**Decision**: Phase 10 closes after confirming metric granularity thesis. All future retrieval work requires a new Phase and OpenSpec change.

**Context**: Doc-ID Recall@10 = 91.9%. 32/41 (78%) wrong cases reclassified as metric granularity. The remaining misses are: 7 zero-hit (query expansion), 32 partial-hit (fusion ranking), 9 genuine misses. These are diagnosed but not addressed — they become future Phase candidates.

**Rationale**: Continuing retrieval optimization within Phase 10 would blur scope. The thesis is confirmed; further work should be planned as independent phases with clear hypotheses.

**Alternatives**: Keep Phase 10 open (scope creep risk), declare retrieval done (premature).

---

## AD-2026-05-06: Controller Harness Is Canonical Source of Truth

**Decision**: GitHub `docs/harness/*.md` files (chatgpt_controller_context.md, controller_next_actions.md, controller_session_log.md, controller_decision_log.md) are the source of truth for AI handoff. Notion is human-facing only.

**Context**: Four files serve distinct roles: context (project state snapshot), next actions (batch scope + allowed/forbidden files), session log (structured handoff summaries), decision log (key decisions with rationale).

**Rationale**: GitHub files are version-controlled, portable across AI tools, and survive window resets.

---

## AD-2026-05-06: reports/harness/ for Operational Logs

**Decision**: Create `reports/harness/` for operational logs (engineering, error, validation, architecture decisions). These supplement but do not replace `docs/harness/` controller files.

**Context**: `docs/harness/` is for controller handoff — concise, structured, actionable. `reports/harness/` is for detailed operational records that inform but are not required reading for every handoff.

**Rationale**: Separation of concerns — handoff files stay concise; operational detail lives in reports/harness/ and is read on demand.
