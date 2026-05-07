# Design: Guard-Aware Provider Prompting

## Architecture

### Before (Phase 13.9)

`OpenAICompatibleProvider.generate_draft()` used a hardcoded minimal prompt:

```
你是一个客服工单处理助手。根据用户消息和检索到的证据，生成一个专业的回复草稿。
回复必须基于提供的证据，不要编造信息。如果无法找到相关证据，说明无法确认并建议转人工。
回复用中文。

用户消息：{text}
问题类型：{issue_type}
风险标记：{flags}
严重度：{severity}
检索到的证据：
[1] Title: content...
[2] Title: content...
...
请生成回复草稿：
```

Evidence formatted as `[1]`, `[2]` — no chunk_id format.

### After (Phase 13.10)

Replace with structured prompt that:
1. Uses evidence block with `[chunk_id]` format (matching existing `format_evidence_block()`)
2. Adds guard-aware citation instruction in safety rules
3. Explicitly forbids numeric `[N]` citations
4. Adds fallback instruction if evidence insufficient

New system prompt:
```
你是一名客服工单处理助手。请根据用户消息和检索到的证据，生成一个专业的回复草稿。
回复必须基于提供的证据，不要编造信息。如果无法找到相关证据，说明无法确认并建议转人工。
回复用中文。
```

New user prompt format (with evidence blocks and safety instructions):
```
用户消息：{text}
问题类型：{issue_type}
风险标记：{flags}
严重度：{severity}

## 可用证据
（证据1）
[chunk_id]: {ev1.chunk_id}
[内容]: {ev1.content[:200]}

（证据2）
[chunk_id]: {ev2.chunk_id}
[内容]: {ev2.content[:200]}

## 安全与约束规则
1. 每一条事实性或政策性陈述都必须引用对应的chunk_id，格式为 [{chunk_id}]。
   不要使用 [1]、[2] 等数字格式——必须使用证据块中的 chunk_id。
2. 如果证据不足以回答客户问题，必须说明需要转人工处理。
3. 禁止承诺退款金额、赔偿、法律行动、账户变更或任何未在证据中明确支持的内容。
4. 禁止承认法律责任或做出超出证据范围的保证。
5. 禁止承诺解决时间线或保证特定结果。
6. 所有回复必须以草稿形式呈现，不得使用最终确认语气。
7. 本工单严重程度为「{severity}」...

请生成回复草稿（在回复中每引用一条证据，必须在对应句子后加上 [{chunk_id}] 标记）：
```

## Key Design Decisions

1. **Reuse evidence block format**: Use `format_evidence_block()` output (with `[chunk_id]` already present) as the evidence section. This ensures consistency with `prompt_builder.py`.

2. **Cite by chunk_id only**: Explicitly require `[{chunk_id}]` format, not `[1]`, `[2]`. This matches what claim guard's `_extract_chunk_ids()` recognizes.

3. **Backward compatibility**: FakeLLMProvider template already uses `[chunk_id]` format. No changes needed to FakeLLMProvider or quality gate.

4. **No schema change**: DraftReply schema unchanged. CitationValidator and ClaimGuard unchanged.

5. **No new dependencies**: All prompt text is hardcoded in llm_provider.py.
