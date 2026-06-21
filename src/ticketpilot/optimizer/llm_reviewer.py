"""LLM-based reviewer for keyword trade-offs.

Uses the OpenAI-compatible API to evaluate whether a proposed keyword
addition is worth the trade-off (fix count vs regression count).
"""

from __future__ import annotations

import json
import os

from openai import OpenAI

from ticketpilot.optimizer.config import OptimizerConfig
from ticketpilot.optimizer.tradeoff import KeywordTradeoff


# The prompt template
REVIEW_PROMPT = """You are a keyword tuning expert for a Chinese customer service intent classifier.

Evaluate this proposed change:

KEYWORD: "{keyword}"
TARGET INTENT: {target_intent}
CASES FIXED: {fixed_count} — these cases were misclassified and would now be correct
CASES HARMED: {harmed_count} — these cases were correct and would now be wrong
NET GAIN: {net_gain}
SAMPLE FIXED CASES:
{fixed_samples}
SAMPLE HARMED CASES:
{harmed_samples}

Rules:
1. If net_gain > 0, lean toward APPROVE (even +1 is an improvement)
2. If net_gain <= 0, REJECT unless the harmed cases are low-severity (e.g. product_consulting)
3. If keyword is too generic (like "东西", "一个", "这个"), REJECT
4. If keyword is a platform name or product name (like "拼多多", "iPhone"), APPROVE — these are strong intent signals

Respond with JSON only:
{{"decision": "APPROVE" | "REJECT", "reasoning": "..."}}
"""


def _llm_complete(prompt: str, config: OptimizerConfig) -> str:
    """Call the configured LLM via openai library and return the response text."""
    api_key = config.llm_api_key or os.getenv("OPTIMIZER_LLM_API_KEY", "")
    if not api_key:
        raise ValueError(
            "No LLM API key configured. "
            "Set OPTIMIZER_LLM_API_KEY env var or llm_api_key in OptimizerConfig."
        )
    client = OpenAI(api_key=api_key, base_url=config.llm_base_url)
    response = client.chat.completions.create(
        model=config.llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1,
        timeout=30,
    )
    # Handle both standard OpenAI SDK response and plain string (e.g. OpenCode API)
    if isinstance(response, str):
        return response
    return response.choices[0].message.content


def review_keyword(
    tradeoff: KeywordTradeoff,
    sample_fixed: list[str],
    sample_harmed: list[str],
    config: OptimizerConfig | None = None,
) -> dict:
    """Ask the LLM to review a keyword addition.

    Args:
        tradeoff: The tradeoff analysis result.
        sample_fixed: Sample text of fixed cases (max 3).
        sample_harmed: Sample text of harmed cases (max 3).
        config: OptimizerConfig with LLM settings. Uses defaults if None.

    Returns:
        dict with "decision" ("APPROVE" | "REJECT") and "reasoning" keys.
    """
    if config is None:
        config = OptimizerConfig()

    prompt = REVIEW_PROMPT.format(
        keyword=tradeoff.keyword,
        target_intent=tradeoff.target_intent,
        fixed_count=len(tradeoff.fixed_case_ids),
        harmed_count=len(tradeoff.harmed_case_ids),
        net_gain=tradeoff.net_gain,
        fixed_samples="\n".join(f'- "{t[:80]}"' for t in sample_fixed[:3]),
        harmed_samples="\n".join(f'- "{t[:80]}"' for t in sample_harmed[:3]),
    )

    response_text = _llm_complete(prompt, config)
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        return {
            "decision": "REJECT",
            "reasoning": f"Failed to parse LLM response: {response_text[:200]}",
        }
