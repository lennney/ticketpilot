# Error Log — TicketPilot

*Tracks errors encountered during development, their root causes, and resolutions.*

---

## 2026-05-06 — Phase 10.7.5: Stale Export Rows JSON

- **Error**: Existing `phase10_real_doc_level_rows.json` only had 14 doc_ids (from Phase 10.5.1 P0 eval).
- **Root Cause**: Re-export was needed after Phase 10.7 expanded labels to 86 cases.
- **Fix**: Re-ran real pipeline export to regenerate rows JSON with all 86 doc_ids.
- **Prevention**: Added `--force` semantics to export mode; documented that export must be re-run after label expansion.

---

## 2026-05-06 — Phase 10.7.5: GBK UnicodeDecodeError

- **Error**: `UnicodeDecodeError: 'gbk' codec can't decode byte...` when reading JSON from Windows Python.
- **Root Cause**: Windows python3.exe resolves instead of WSL Python when invoked from WSL bash, defaulting to system encoding.
- **Fix**: Used `uv run python` instead of bare `python3`; specified `encoding='utf-8'`.
- **Prevention**: Always use `uv run python` in this repo; never rely on bare `python3`.

---

## 2026-05-06 — Phase 10.7.5: AttributeError on None.strip()

- **Error**: `AttributeError: 'NoneType' object has no attribute 'strip'` in `label_full_doc_level.py`.
- **Root Cause**: `csv.DictReader` returns `None` for empty CSV cells; `r.get("field", "").strip()` fails when cell is None.
- **Fix**: Changed to `(r.get("field") or "").strip()`.
- **Prevention**: Defensive CSV cell access pattern.

---

## 2026-05-06 — Phase 10.9: OpenSpec Archive Required Task Completion

- **Error**: `openspec archive` failed due to incomplete tasks in tasks.md.
- **Root Cause**: Tasks 1.6, 1.7, 1.8, 9.1-9.5, 9.7 were not marked as done.
- **Fix**: Marked tasks as done, then re-ran with `-y` flag to skip interactive prompt.
- **Prevention**: Verify all tasks are complete before archive attempt.
