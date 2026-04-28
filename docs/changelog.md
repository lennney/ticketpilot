# TicketPilot Changelog

## 2026-04-29 - Initialize development management workflow

### Changed
- Initialized TicketPilot project structure.
- Added uv-based Python project setup.
- Added Docker Compose configuration for PostgreSQL + pgvector.
- Added environment template without secrets.
- Prepared Claude Code agents and skills directories.
- Prepared documentation and quality gate structure.

### Why
- To support spec-driven, traceable, AI-assisted development.
- To prevent uncontrolled code generation and requirement drift.

### Tests / Evaluation
- No product code yet.
- Quality gate script will be added in this initialization stage.

### Remaining risks
- No backend workflow implemented yet.
- No database schema implemented yet.
- No evaluation cases yet.
