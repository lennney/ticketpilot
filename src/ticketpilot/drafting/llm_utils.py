"""LLM calling utilities for the draft agent.

Exports:
    LlmConfig: Dataclass holding LLM endpoint configuration.
    call_llm: Make a chat-completion call to an OpenAI-compatible endpoint.
    extract_json: Parse JSON from LLM output (handles markdown fences).
    _SYSTEM_PROMPT: The shared system prompt used by generation, reflection,
        and search refinement modules.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# System prompt — shared by generation, reflection, and search_refiner
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """\
你是一名客服工单处理智能助手（DraftAgent）。
你的任务是根据客户消息，使用提供的工具检索知识库，然后生成基于证据的专业回复。

## 可用工具

### 1. search_knowledge
用途：在知识库中搜索与客户问题相关的证据（FAQ、政策、案例）。
输入格式：
```json
{"tool": "search_knowledge", "query": "搜索关键词"}
```

### 2. get_policy_by_code
用途：根据政策编号查找具体政策内容。
输入格式：
```json
{"tool": "get_policy_by_code", "code": "1.2.3"}
```

## 工作流程

1. 首先使用 search_knowledge 检索证据
2. 评估检索到的证据质量（相关性评分、内容覆盖度）
3. 如果证据不足，尝试用不同的关键词重新搜索
4. 基于证据生成回复草稿
5. 自我检查回复是否基于证据，有无编造内容

## 安全规则

- 回复必须基于检索到的证据，禁止编造信息
- 禁止承诺退款金额、赔偿金额、法律行动、账号变更
- 禁止承诺解决时间线或保证特定结果
- 禁止承认法律责任或做出超出证据范围的保证
- 如果证据不足以回答客户问题，必须建议转人工处理
- 引用证据时使用 [证据ID] 格式

## 输出格式

当需要调用工具时，输出：
```json
{"tool": "工具名", "参数名": "参数值"}
```

当准备好生成最终回复时，输出：
```json
{
  "step": "reply",
  "draft_text": "回复内容",
  "cited_evidence_ids": ["证据ID1", "证据ID2"],
  "confidence": 0.8,
  "unsupported_claims": ["无法支持的内容（如有）"],
  "missing_information": ["缺失信息（如有）"],
  "safety_notes": ["安全说明（如有）"]
}
```"""


# ---------------------------------------------------------------------------
# LLM configuration dataclass
# ---------------------------------------------------------------------------


@dataclass
class LlmConfig:
    """Configuration passed to :func:`call_llm`."""

    base_url: str
    api_key: str
    model: str
    timeout: int
    max_tokens: int
    temperature: float


# ---------------------------------------------------------------------------
# LLM call helper
# ---------------------------------------------------------------------------


def call_llm(
    messages: list[dict[str, str]],
    config: LlmConfig,
) -> str:
    """Make a single chat completion call to the LLM endpoint.

    Args:
        messages: OpenAI-format message list.
        config: LLM endpoint configuration.

    Returns:
        The response content string (empty on failure).
    """
    payload = {
        "model": config.model,
        "messages": messages,
        "max_tokens": config.max_tokens,
        "temperature": config.temperature,
    }
    req = urllib.request.Request(
        f"{config.base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=config.timeout) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    return result.get("choices", [{}])[0].get("message", {}).get("content", "")


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------


def extract_json(text: str) -> dict[str, Any] | None:
    """Extract a JSON object from LLM output (handles markdown fences).

    Tries, in order:
    1. A JSON block inside a markdown code fence (`` ```json ``).
    2. The entire text parsed as JSON.
    3. The first ``{ ... }`` block in the text.

    Returns the parsed dict or ``None``.
    """
    # Try to find JSON block in markdown code fence
    match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Try parsing the entire text as JSON
    try:
        return json.loads(text.strip())
    except json.JSONDecodeError:
        pass
    # Try to find first { ... } block
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None
