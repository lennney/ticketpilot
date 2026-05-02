# TicketPilot Development Timeline

## 2026-04-29 — Project Origin

| Commit | Description |
|--------|-------------|
| `91f388f` | chore: initialize TicketPilot development workflow |
| `0c52f5e` | chore: add dev dependencies, .gitkeep dirs, fix quality gate secret pattern |
| `089c5ba` | chore: update local development ignores |
| `ecd1de6` | spec: add ticket intake risk triage change |
| `ee513a2` | spec: add layered knowledge retrieval foundation |
| `dbec010` | chore: add AI-assisted development supervision workflow |
| `69de63e` | chore: add project audit agent and skill |
| `09bd8ea` | audit: project plan audit 2026-04-29 — HOLD_NEW_FEATURES |

## 2026-04-30 — Audit Remediation (fix/audit-blockers)

| Commit | Description |
|--------|-------------|
| `44f5dbb` | fix: Batch A — quality gate and documentation truthfulness (BLOCK-1, BLOCK-5) |
| `588cf1d` | fix: Batch B — sync technical_decisions.md, fix docker volume, annotate seed migration (GAP-9, GAP-10, GAP-12) |
| `d963c30` | fix: Batch C — two-layer source table architecture (BLOCK-2) |
| `9738f37` | Merge branch 'fix/audit-blockers' |
| `a579e36` | chore: normalize file mode |

## 2026-04-30 — Pipeline Integration (connect-retrieval-to-intake-risk-pipeline)

*Commit history for this change is embedded in the merge commit `9738f37` (fix/audit-blockers branch was the active branch when pipeline batches were committed). The pipeline integration work was implemented in four batches:*

| Batch | Scope | Tests |
|-------|-------|-------|
| A | Schema extension (EvidenceCandidate, TicketOutput) | 20 new unit tests |
| B | Query construction logic | 13 new unit tests |
| C | Pipeline integration (Stage 4) | 10 new unit tests |
| D | Export cleanup + integration tests + quality gate | 6 new integration tests |

## 2026-05-01 — Archive Prior Stages

| Commit | Description |
|--------|-------------|
| `22e782a` | chore: track accepted TicketPilot implementation |
| `55ed46e` | chore: archive intake risk triage OpenSpec change |
| `ce58ba0` | chore: archive add-layered-knowledge-retrieval-foundation OpenSpec change |

## 2026-05-02 — Evidence Draft Generation (add-evidence-draft-generation)

| Commit | Description |
|--------|-------------|
| `e30ff5d` | feat: add evidence-grounded drafting foundation |
| `320840f` | feat: add standalone evidence draft generation |
| `b7c5e4f` | test: harden standalone draft generation checks |
| `ff7e8bd` | feat: add optional pipeline draft entrypoint |
| `58bb199` | test: add drafting workflow integration coverage |
| `0a7dd5c` | docs: finalize evidence draft generation decisions |
| `afa8885` | chore: archive evidence draft generation OpenSpec change |

## 2026-05-02 — Human Review Console (add-human-review-console)

| Commit | Description |
|--------|-------------|
| `38ff0b4` | spec: add human review console OpenSpec change |
| `6e33746` | feat: add review schema and JSONL store foundation |
| `86a162c` | feat: add reviewer_label to ReviewDecision schema |
| `d2f08e2` | feat: add review_trigger_reasons to ReviewDecision schema |
| `7014fa3` | feat: add Streamlit human review console MVP |
| `ac1ba23` | test: finalize human review console coverage |
| `def4afa` | chore: archive human review console OpenSpec change |

## 2026-05-02 — Pre-Batch 1 Documentation Hygiene

| Commit | Description |
|--------|-------------|
| `9890696` | docs: inventory and deconflict legacy documentation |

## Legend

- **2026-04-29**: Project setup, spec creation, audit
- **2026-04-30**: Audit blockers resolved (quality gate, schema), pipeline integration
- **2026-05-01**: Prior stage archiving
- **2026-05-02**: Draft generation, review console, documentation hygiene
