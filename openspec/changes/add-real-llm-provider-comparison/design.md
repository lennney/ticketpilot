# Design: Real LLM Provider Offline Comparison

## Architecture

```
LLMProvider (ABC)
  ├─ FakeLLMProvider (default, deterministic, no network)
  └─ OpenAICompatibleProvider (opt-in, env-only API key)
```

Same pattern as embedding provider (FakeEmbeddingProvider / OpenAICompatibleProvider).

## Provider Behavior

OpenAICompatibleProvider:
- Reads `TICKETPILOT_LLM_PROVIDER=openai_compatible` to activate
- Reads `TICKETPILOT_LLM_BASE_URL`, `TICKETPILOT_LLM_API_KEY`, `TICKETPILOT_LLM_MODEL`, `TICKETPILOT_LLM_TIMEOUT_SECONDS`, `TICKETPILOT_LLM_MAX_TOKENS`, `TICKETPILOT_LLM_TEMPERATURE`
- If env vars missing, raises clear ValueError — does NOT silently fall back
- Never logs or prints API key
- Handles invalid JSON: returns safe fallback DraftReply, sets unsupported_claims, forces must_human_review
- Handles network errors: returns safe fallback DraftReply with escalation_reason

## Config Changes

provider_config.py: extend allowed providers, add OpenAICompatibleProvider creation branch.

## Comparison Runner

scripts/run_phase12_llm_provider_comparison.py:
- Always runs FakeLLMProvider → generates fake baseline
- If TICKETPILOT_LLM_PROVIDER=openai_compatible: runs OpenAICompatibleProvider
- If real provider env missing: still generates fake baseline, writes "real: not configured"
- Computes same metrics for both providers
- Writes row-level JSON, summary JSON, markdown report

## Safety Layers

1. Fake default (no API key needed)
2. Env-only activation (not code-level)
3. Safe fallback on errors
4. No API key in logs/reports
5. Quality gate does not require real API key