# Repair Playbook — TicketPilot AI Development Harness

*Categorized repair procedures for common harness errors.*

---

## Integration Tests Skipped

### Symptoms
- Quality gate shows `N skipped` integration tests
- Archive attempt fails due to skipped tests

### Likely Causes
- Database not available
- Test marked with `pytest.skip()` without proper reason
- Integration test inherits skipping from conftest

### First Checks
1. Check `TICKETPILOT_SKIP_DB_TESTS` environment variable
2. Verify Docker container is running: `docker compose ps`
3. Check test file for unconditional `pytest.skip()`
4. Run integration tests individually to isolate

### Safe Repair Steps
- If DB unavailable: set `TICKETPILOT_SKIP_DB_TESTS=1` before running quality gate
- If test unconditionally skipped: remove skip or add proper skip reason
- If conftest auto-skips: verify DB connection works first

### Commands
```bash
docker compose up -d
uv run pytest tests/integration/ -v --tb=short
```

### Stop Conditions
- Do NOT treat skipped tests as pass for archive
- Do NOT force-merge PR with skipped integration tests

### When to Escalate
- If DB always unavailable in environment (not just local)
- If test has legitimate dependency on external service

---

## OpenSpec Validation Failure

### Symptoms
- `openspec validate <change-id> --strict` fails
- Missing requirement (SHALL/MUST) or scenario format

### Likely Causes
- Requirement without SHALL/MUST
- Missing scenario blocks
- Delta format incorrect
- Missing Purpose section

### First Checks
1. Run `openspec validate <change-id> --strict` for exact error
2. Check spec file for SHALL/MUST keywords
3. Verify scenario format (#### Scenario: ...)
4. Check for ## Purpose section header

### Safe Repair Steps
1. Add SHAL L/MUST to requirement description
2. Add scenario blocks with Given/When/Then format
3. Add ## Purpose section if missing
4. Run validation again

### Commands
```bash
openspec validate <change-id> --strict
openspec validate --all
```

### Stop Conditions
- Do NOT skip OpenSpec validation
- Do NOT archive without passing --strict

### When to Escalate
- If error message is unclear about what to fix
- If existing spec format doesn't match

---

## Ruff Failure

### Symptoms
- `uv run ruff check .` fails
- F401 (unused import), F541 (f-string without format), etc.

### Likely Causes
- Unused import added
- Format string error
- Line too long
- Import order issue

### First Checks
1. Read exact ruff error message
2. Check which file and line
3. Determine if change introduced the issue

### Safe Repair Steps
1. If unused import: remove it
2. If f-string without format: add format specifier or use regular string
3. If line too long: split line or reduce verbosity
4. If import order: run `uv run ruff check --fix .`

### Commands
```bash
uv run ruff check .
uv run ruff check --fix .
```

### Stop Conditions
- Do NOT use `# noqa` without justification comment
- Do NOT add `# noqa: F401` for unrelated unused imports

### When to Escalate
- If false positive (code is correct but ruff complains)
- If fix would make code less readable

---

## Coverage Drop

### Symptoms
- `pytest --cov` shows coverage below 70%
- Quality gate fails on coverage

### Likely Causes
- New code not covered by tests
- Test file deleted or skipped
- Module coverage data missing

### First Checks
1. Check coverage report for uncovered files
2. Identify which module has low coverage
3. Check if tests exist for that module

### Safe Repair Steps
1. Add unit tests for uncovered code
2. Or identify if code is dead/unused and should be removed
3. If newly added module, ensure tests exist

### Commands
```bash
uv run pytest --cov=src/ticketpilot --cov-report=term-missing
```

### Stop Conditions
- Do NOT lower coverage threshold to pass
- Do NOT remove coverage check

### When to Escalate
- If legitimate untestable code (e.g., __init__.py with imports)
- If coverage tool misconfigured

---

## Secret Scan Failure

### Symptoms
- Quality gate shows "API key found in diff"
- `sk-` pattern detected in changed files

### Likely Causes
- API key added to source code
- .env file committed
- Authorization header in code
- Token in string literal

### First Checks
1. Run `git diff` to find the secret
2. Check which file contains the secret
3. Determine if it's test data or real secret

### Safe Repair Steps
1. Remove the secret from code
2. Move to .env.local if needed locally
3. If real secret committed: rotate immediately
4. Rewrite git history if secret is in older commits

### Commands
```bash
git diff | grep -i "sk-"
grep -r "sk-" . --include="*.py"
```

### Stop Conditions
- Do NOT commit any secret
- Do NOT push with secret in history

### When to Escalate
- If real production secret was exposed
- If git history rewrite needed (high risk)

---

## Overclaim Scan Failure

### Symptoms
- Report contains "production-ready", "real-world benchmark", "真实线上效果"
- Quality gate overclaim check fails

### Likely Causes
- Report generated with overclaiming language
- Marketing copy added to technical doc
- Scope boundary not properly stated

### First Checks
1. Search for overclaiming phrases in changed files
2. Check report scope section
3. Verify boundary wording is present

### Safe Repair Steps
1. Add explicit scope boundary: "local demo / portfolio prototype"
2. Add NOT a production benchmark disclaimer
3. Remove any real-world or production claims

### Commands
```bash
grep -r "production-ready\|real-world\|真实线上\|行业 benchmark" reports/
```

### Stop Conditions
- Do NOT claim real-world validation
- Do NOT claim production readiness

### When to Escalate
- If boundary wording cannot safely fix the claim
- If document serves different purpose (e.g., external marketing)

---

## Provider Env/Config Failure

### Symptoms
- `TICKETPILOT_LLM_PROVIDER=openai_compatible` but env vars missing
- ValueError raised for missing BASE_URL or API_KEY

### Likely Causes
- Real provider configured but not all env vars set
- API key not in environment
- BASE_URL not configured

### First Checks
1. Check TICKETPILOT_LLM_PROVIDER value
2. Verify TICKETPILOT_LLM_BASE_URL is set
3. Verify TICKETPILOT_LLM_API_KEY is set

### Safe Repair Steps
1. If real provider not needed: unset TICKETPILOT_LLM_PROVIDER (use fake)
2. If real provider needed: configure all required env vars in .env.local
3. Never commit .env.local

### Commands
```bash
echo "TICKETPILOT_LLM_PROVIDER: ${TICKETPILOT_LLM_PROVIDER:-not set}"
echo "TICKETPILOT_LLM_BASE_URL: ${TICKETPILOT_LLM_BASE_URL:+set}"
```

### Stop Conditions
- Do NOT commit .env or .env.local
- Do NOT hardcode API keys

### When to Escalate
- If real provider needed for batch validation
- If env var configuration is unclear

---

## DB/Postgres/pgvector Failure

### Symptoms
- Integration tests fail with connection error
- `psycopg.errors.ConnectionFailure` or similar

### Likely Causes
- Docker container not running
- Database not initialized
- pgvector extension not installed
- Connection pool exhausted

### First Checks
1. Check Docker status: `docker compose ps`
2. Verify database is running: `docker exec <container> psql -c "SELECT 1"`
3. Check pgvector extension: `docker exec <container> psql -c "SELECT * FROM pg_extension WHERE extname='vector'"`

### Safe Repair Steps
1. Start Docker: `docker compose up -d`
2. Re-run seed: `uv run python -c "from ticketpilot.retrieval.db.seeding import seed_knowledge_chunks; seed_knowledge_chunks(clear_existing=True)"`
3. If database corrupted: drop and recreate

### Commands
```bash
docker compose up -d
docker compose logs postgres
uv run python -c "from ticketpilot.retrieval.db.seeding import seed_knowledge_chunks; seed_knowledge_chunks(clear_existing=True)"
```

### Stop Conditions
- Do NOT run integration tests without DB
- Do NOT skip all integration tests without DB check

### When to Escalate
- If Docker always fails on this system
- If pgvector installation fails

---

## Network/Push Failure

### Symptoms
- `git push` fails
- `curl` or `urllib` timeout
- TLS certificate error

### Likely Causes
- Network connectivity issue
- Git authentication expired
- Proxy blocking connection
- Remote repository unavailable

### First Checks
1. Check git remote: `git remote -v`
2. Test network: `curl -I https://github.com`
3. Verify git credentials: `gh auth status`

### Safe Repair Steps
1. Retry push after network stabilizes
2. Re-authenticate with git if needed
3. Check proxy settings if behind corporate firewall
4. Use SSH instead of HTTPS if available

### Commands
```bash
git remote -v
curl -I https://github.com 2>&1 | head -5
git push --force-with-lease  # only if safe
```

### Stop Conditions
- Do NOT force push to main/master
- Do NOT skip push after validation

### When to Escalate
- If git authentication repeatedly fails
- If network always unavailable

---

## Real Provider Not Configured

### Symptoms
- Comparison runner shows "Real provider not configured"
- TICKETPILOT_LLM_PROVIDER not set

### Likely Causes
- Real provider env vars not set
- .env.local not configured
- Provider intentionally not configured for offline comparison

### First Checks
1. Check if TICKETPILOT_LLM_PROVIDER is set
2. Verify BASE_URL and API_KEY presence
3. Determine if real provider run is needed for batch

### Safe Repair Steps
1. If not needed: run with fake provider only
2. If needed: configure .env.local with required vars
3. Never commit .env.local

### Commands
```bash
echo "TICKETPILOT_LLM_PROVIDER: ${TICKETPILOT_LLM_PROVIDER:-not set}"
```

### Stop Conditions
- Do NOT proceed with real provider if API key missing
- Do NOT commit .env.local

### When to Escalate
- If batch explicitly requires real provider comparison
- If configuration instructions are unclear

---

## Report/Generated File Drift

### Symptoms
- Report JSON/MD shows stale data
- Exported file doesn't match current state
- Old commit hash in report

### Likely Causes
- Report not regenerated after changes
- Export script not re-run
- Cached data used instead of fresh run

### First Checks
1. Check report timestamp
2. Check if related code changed since report
3. Verify commit hash in report

### Safe Repair Steps
1. Re-run export/generation script
2. Verify report contains current data
3. Update timestamp if needed

### Commands
```bash
python scripts/run_phase12_llm_provider_comparison.py --limit 5
python scripts/run_draft_evaluation.py
```

### Stop Conditions
- Do NOT commit stale reports
- Do NOT modify archived Phase reports

### When to Escalate
- If export script is broken
- If archived report needs correction (rare)

---

## General Debugging Pattern

When encountering unknown error:
1. Read exact error message
2. Identify which command failed
3. Check recent changes (git diff)
4. Search error_memory.jsonl for similar issue
5. Apply repair from playbook or create new entry
6. Validate fix before proceeding

---

## Evidence Panel Grouping

### Symptoms
- Evidence items displayed without structure
- User cannot quickly scan items by doc_type

### Likely Causes
- Flat list rendering without grouping
- Missing count display per group

### Safe Repair Steps
1. Group items by doc_type using dict: `grouped.setdefault(item.doc_type, []).append(item)`
2. Iterate groups in fixed order: `DOC_TYPE_ORDER = ["FAQ", "POLICY", "CASE"]`
3. Show count in subheader: `f"{emoji} {doc_type} ({len(items)})"`
4. Handle empty groups gracefully (omit or show placeholder)

### Code Pattern
```python
grouped = {}
for item in evidence_items:
    grouped.setdefault(item.doc_type, []).append(item)

for doc_type in DOC_TYPE_ORDER:
    if doc_type in grouped:
        items = grouped[doc_type]
        # render group with emoji and count
```

### Commands
```bash
uv run pytest tests/unit/test_chat_adapter.py::TestEvidencePanelGrouping -v
```

---

## Citation Marker Mapping

### Symptoms
- Draft text contains raw placeholders like `[ID:xxx]`
- Reference list not human-readable

### Likely Causes
- Placeholders not mapped to human-readable labels
- Missing title fallback for references

### Safe Repair Steps
1. Build marker map from source data: `marker_map = {item.chunk_id: f"[{item.doc_type}] {item.title}"}`
2. Apply regex replacement for placeholders
3. Provide fallback: `item.title or item.chunk_id[:8]`
4. Handle unknown citations gracefully

### Code Pattern
```python
# Build marker map
marker_map = {
    item.chunk_id: f"[{item.doc_type.upper()}] {item.title or item.chunk_id[:8]}"
    for item in source_items
}

# Replace placeholders
draft = re.sub(r'\[ID:(\w+)\]|\[(\w+)\]', lambda m: marker_map.get(m.group(1) or m.group(2), m.group(0)), draft)
```

### Commands
```bash
uv run pytest tests/unit/test_chat_adapter.py::TestInlineCitationMarkers -v
```

---

## Prevention Rules Summary

- Always use `uv run python` instead of bare `python3`
- Always verify OpenSpec tasks complete before archive
- Never commit secrets or .env files
- Never treat skipped integration tests as pass
- Always re-run export after label expansion
- Always specify encoding='utf-8' for file I/O
- Always use defensive CSV cell access: `(r.get('field') or '').strip()`
- Always update tasks.md checkbox when phase completes
- Always verify ARCHITECTURE.md phase descriptions match tasks.md