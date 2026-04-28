---
name: secure-coding
description: Use when adding API providers, environment variables, external services, logs, deployment configs, or documentation that may expose secrets.
---

# Secure Coding

Rules:
1. Never hardcode API keys, tokens, or secrets.
2. Use environment variables or local untracked config.
3. Provide .env.example only.
4. Do not print secrets in logs.
5. Do not include secrets in README, tests, screenshots, or committed files.
