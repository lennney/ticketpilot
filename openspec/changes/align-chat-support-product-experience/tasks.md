# Tasks: Align Chat Support Product Experience

## Task List

- [x] 15.1: Product Re-alignment Planning
  - Create proposal.md, design.md, tasks.md, spec.md
  - Run OpenSpec strict and --all validation
  - Update harness docs
  - No runtime code changes

- [x] 15.2: Chat Demo UI Skeleton
  - Create `src/ticketpilot/chat/` module
  - Define `ChatMessage`, `ChatSession`, `ChatState`, `ChatDisplay` schemas
  - Define `ChatContext` and `EvidenceDisplayItem` for multi-turn support
  - Add `append_message()` and `update_context_from_message()` pure helpers
  - Build Streamlit chat UI with context panel + skeleton panels
  - No backend logic yet (pipeline integration in Phase 15.3)

- [x] 15.3: Pipeline-to-Chat Adapter
  - Implement `ticket_output_to_chat_display()` in adapter.py
  - Implement `evidence_to_display_items()` helper
  - Implement `chat_display_to_context_metadata()` helper
  - Wire pipeline output to chat UI display
  - Risk decision matrix: severity × evidence × guard → human_review_required
  - 29 unit tests
  - Full quality gate passed: 1166 unit + 146 integration, 0 skipped, 83.68%

- [x] 15.4: Risk Escalation Display
  - Show risk_badge (LOW/MEDIUM/HIGH) with color coding
  - Show risk_flags as human-readable list
  - Show human_review_required status
  - Connect to pipeline risk assessment output

- [x] 15.5: Evidence and Draft Panel
  - Show evidence panel grouped by type (FAQ/Policy/Case)
  - Show AI draft with inline citation markers
  - Show guard_passed status and failure_reasons
  - Show citation_ids inline in draft

- [x] 15.6: Human Review Queue Link
  - Connect "进行人工审核" button to existing review console
  - Pass ChatSession context to review console
  - Show review decision in chat after reviewer acts

- [x] 15.7: Portfolio Story Update
  - Update README.md with chat demo description
  - Update product_portfolio_material_pack.md with new product direction
  - Update interview_talking_points.md
  - Update all portfolio docs to reflect chat support narrative

- [ ] 15.8: Final Validation and Archive
  - Full quality gate: unit + integration, 0 skipped, coverage >= 70%
  - Ruff clean, OpenSpec --all pass, secret scan clean
  - Archive OpenSpec change
  - Update harness docs

## Dependencies

- 15.1 must complete before 15.2–15.8
- 15.2 must complete before 15.3
- 15.3 must complete before 15.4, 15.5
- 15.4, 15.5 must complete before 15.6
- 15.6 must complete before 15.7
- 15.7 must complete before 15.8

## Exit Criteria

- Chat demo UI shows user input → AI draft flow
- Risk badge + risk_flags visible in UI
- Evidence panel shows retrieved evidence
- Guard result visible in UI
- Human review button appears when required
- No auto-send — all drafts are demo only
- Human-in-the-loop — high risk always requires review
- Full quality gate: unit + integration, 0 skipped, coverage >= 70%
- No API key in tracked files
- No production-ready claims in docs
