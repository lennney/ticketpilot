"""Multi-query expansion using LLM for improved retrieval recall.

Generates query variants by asking an LLM to rephrase the original query
from different semantic angles. Falls back to original query on failure.
"""
from __future__ import annotations

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

_EXPANSION_PROMPT = """\
你是一个搜索查询优化器。给定一个客服工单查询，生成 {n} 个不同角度的搜索关键词变体。
要求：
- 每个变体 5-15 个字
- 覆盖不同语义角度（同义词、上位词、具体场景）
- 不要重复原始查询
- 只输出 JSON 数组，不要解释

查询：{query}
意图：{intent}

输出格式：["变体1", "变体2"]
"""


class MultiQueryExpander:
    """Generate query variants using LLM for improved recall.

    Uses the same LLM endpoint as DraftAgent (configured via env vars).
    Falls back to returning only the original query on any failure.
    """

    def __init__(
        self,
        num_variants: int = 2,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int = 15,
    ) -> None:
        self._num_variants = num_variants
        self._base_url = (
            base_url
            or os.environ.get("TICKETPILOT_LLM_BASE_URL", "https://api.deepseek.com")
        ).rstrip("/")
        self._api_key = api_key or os.environ.get("TICKETPILOT_LLM_API_KEY", "")
        self._model = model or os.environ.get("TICKETPILOT_LLM_MODEL", "deepseek-chat")
        self._timeout = timeout

    def expand(self, query: str, intent: str = "") -> list[str]:
        """Return [original_query, variant_1, variant_2, ...].

        On any failure, returns [original_query] only.
        """
        if not self._api_key:
            logger.debug("No LLM API key, skipping query expansion")
            return [query]

        try:
            variants = self._call_llm(query, intent)
            # Validate variants
            valid = [v for v in variants if self._is_valid_variant(v, query)]
            result = [query] + valid[: self._num_variants]
            logger.info(
                "Query expansion: original_len=%d -> %d variants (total valid: %d)",
                len(query), len(valid[: self._num_variants]), len(valid),
            )
            return result
        except Exception as e:
            logger.warning("Query expansion failed, using original: %s", e)
            return [query]

    def _call_llm(self, query: str, intent: str) -> list[str]:
        """Call LLM to generate query variants."""
        import urllib.request  # noqa: PLC0415

        prompt = _EXPANSION_PROMPT.format(
            n=self._num_variants, query=query, intent=intent
        )
        payload = {
            "model": self._model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "temperature": 0.5,
        }
        req = urllib.request.Request(
            f"{self._base_url}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        return self._parse_variants(content)

    def _parse_variants(self, text: str) -> list[str]:
        """Extract JSON array from LLM response."""
        # Try markdown code fence
        match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(1).strip())
                if isinstance(parsed, list):
                    return [str(v) for v in parsed]
            except json.JSONDecodeError:
                pass

        # Try raw JSON array
        match = re.search(r"\[.*\]", text, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group(0))
                if isinstance(parsed, list):
                    return [str(v) for v in parsed]
            except json.JSONDecodeError:
                pass

        return []

    def _is_valid_variant(self, variant: str, original: str) -> bool:
        """Check if a variant is valid: non-empty, different from original, reasonable length."""
        v = variant.strip()
        if not v or len(v) > 50:
            return False
        if v == original.strip():
            return False
        return True
