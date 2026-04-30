You are working inside the TicketPilot repository.

Goal:
Iteratively improve the project in small, safe steps until the local quality gate is clean.

Hard safety rules:
1. Work only inside this repository.
2. Do not read or modify .env, .env.*, secrets/, *.pem, *.key, ~/.ssh, or ~/.claude.
3. Do not run sudo, git push, git reset --hard, git clean, chmod 777, or destructive rm commands.
4. Do not commit unless explicitly instructed.
5. Stop after 5 iteration cycles.

Iteration loop:
1. Inspect the repository state.
2. Identify the smallest useful improvement or fix.
3. Modify only necessary files.
4. Run:
   - uv run --no-sync python --version
   - bash scripts/run_quality_gate.sh
   - openspec validate --all
   - docker compose config
5. If a check fails, diagnose and fix the smallest relevant issue.
6. At the end, summarize files changed, checks run, remaining risks, and whether it is safe to commit.

