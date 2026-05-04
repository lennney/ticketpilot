# Validation Policy — Change Scope & Required Checks

Defines which validation checks are required based on change scope. The goal is to
match verification effort to risk: docs-only changes need lightweight content review,
while core pipeline changes require the full quality gate.

---

## Change Levels

### Level 1 — Docs / Portfolio Only

**Scope:** `docs/portfolio/`, `docs/demo/`, `docs/technical/` only.

No code, no tests, no OpenSpec changes, no data, no config.

**Required:**
- `git status --short` — confirm only expected files changed
- Content consistency check — numbers, references, claims match project state
- Overclaim / secret scan — `grep` for API keys, personal data, or overstatement

**Not required:**
- `openspec validate` (unless an active change was touched)
- `ruff check`
- `pytest`
- Full quality gate

---

### Level 2 — OpenSpec Scoped Validation

**Scope:** A single active OpenSpec change (`.openspec.yaml`, `proposal.md`, `specs/*`,
`tasks.md`).

**Required:**
- `openspec validate <change-id> --strict` — validates only this change
- `ruff check src tests` — lint the corresponding source files
- Targeted unit tests (per CLAUDE.md test mapping)
- `git status --short`

**Not required:**
- `openspec validate --all` (unless multiple changes were modified)
- Full quality gate

---

### Level 3 — OpenSpec Full Validation

**Scope:** Applies when ANY of the following is true:
- Archiving an OpenSpec change (pre-archive validation)
- Modifying OpenSpec base specs (not just active changes)
- Modifying multiple active changes simultaneously
- Phase / batch closure before commit
- Pre-push validation on a branch with OpenSpec changes

**Required:**
- `openspec validate --all` — validates every spec
- `ruff check src tests`
- Targeted unit tests
- `git status --short`

**Not required:**
- Full quality gate (unless the change also touches core pipeline code)

---

### Level 4 — Full Quality Gate

**Scope:** Applies when ANY of the following is true:
- Core pipeline (`src/ticketpilot/pipeline.py`, `src/ticketpilot/retrieval/`)
- Database schema or migrations
- Data files (`data/eval/`, `data/knowledge/`)
- Evaluation schema or metrics
- OpenSpec archive (pre-archive)
- Pre-push on master / release branches
- Phase / batch final closure

**Required:**
- `./scripts/run_quality_gate.sh`
- Integration tests must pass with **0 skipped** (unless `TICKETPILOT_SKIP_DB_TESTS=1` explicitly set)
- Coverage threshold (≥70%) must be met

**Not allowed:**
- `|| true` to bypass individual checks
- Lowering coverage threshold to pass
- Counting skipped integration tests as pass

---

## Decision Matrix

| Change Scope | OpenSpec Validate | Ruff | Unit Tests | Integration Tests | Quality Gate |
|---|---|---|---|---|---|
| Docs/portfolio only | — | — | — | — | — |
| Single OpenSpec change | scoped`--strict` | ✓ | targeted | — | — |
| Multiple/base OpenSpec | `--all` | ✓ | targeted | — | — |
| Core pipeline / DB / data | `--all` | ✓ | full | ✓ (0 skip) | ✓ |
| Pre-push (any code) | `--all` | ✓ | full | ✓ (0 skip) | ✓ |
| Pre-archive | `--all` | ✓ | full | ✓ (0 skip) | ✓ |
| Phase/batch closure | `--all` | ✓ | full | ✓ (0 skip) | ✓ |

---

## Relationship to `quality_gate.md`

- `docs/technical/quality_gate.md` — describes *what* the quality gate script does
  (its stages, thresholds, design principles).
- `docs/technical/validation_policy.md` (this file) — describes *when* to run each
  check, including when the full quality gate is required vs. when lighter checks
  suffice.

---

## Notes

- "Skipping `openspec validate --all`" does **not** mean "skip validation."
  Choose the appropriate scoped check for the change.
- If unsure, default to the heavier check. Full quality gate is always correct,
  just slower.
- Docs-only still requires a content review: verify numbers, claims, and
  references against the current project state.
