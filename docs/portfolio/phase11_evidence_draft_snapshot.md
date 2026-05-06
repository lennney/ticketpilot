# Phase 11 — Evidence-Grounded LLM Draft Generation

## One-Sentence Summary

Phase 11 built a deterministic evidence-grounded draft generation pipeline that constrains LLM output to retrieved evidence, validates citations and claims, detects forbidden promises, and propagates human review decisions — all without real API calls or network access.

## Diagnosis Chain

| Phase | What | Key Output |
|-------|------|-----------|
| 11.1 | OpenSpec planning | 7 files: proposal, design, tasks, 4 spec files |
| 11.2 | Draft schema + deterministic provider | LLMProvider ABC, FakeLLMProvider, provider config, DraftReply extensions |
| 11.3 | Evidence-grounded prompt builder | DraftPromptInput, build_prompt(), format_evidence_block(), safety instructions |
| 11.4 | Citation validator extension | DraftCitationValidationResult, validate_draft_citations() |
| 11.5 | Unsupported-claim guard | GuardResult, check_claim_guard() with 5 checks |
| 11.6 | Pipeline integration | DraftGenerationResult, generate_draft() wiring all components |
| 11.7 | Human review console update | 15 audit fields, draft_gen_to_audit_fields(), guard display |
| 11.8 | Offline draft evaluation | DraftEvaluationRow, DraftEvaluationSummary, 8 deterministic metrics |

The arc: plan → schema → prompt → validate → guard → integrate → display → evaluate.

## Key Architecture Decisions

### 1. Fake Provider Default

Like FakeEmbeddingProvider for retrieval, FakeLLMProvider is the default for draft generation. Real LLM integration requires explicit opt-in via `TICKETPILOT_LLM_PROVIDER` env var. This ensures:
- No API key required for CI/development
- Deterministic, reproducible behavior
- Pipeline connectivity verified without network calls

### 2. Citation is Evidence-Constraint

The key insight: LLM output is constrained by citation, not just instruction. The prompt builder packs retrieved evidence candidates into the prompt with explicit instructions to cite [N] references. The claim guard then parses [N] markers from draft text to verify coverage.

### 3. Safety Layers Stacked

Eight safety layers stacked in sequence:
1. Prompt constraint (LLM instructed to use evidence only)
2. Citation validation (existing, extended to DraftReply)
3. Claim guard (forbidden promise detection, evidence coverage)
4. Risk-aware check (high-risk flags force escalation acknowledgment)
5. Human review propagation (never downgrades must_human_review)
6. No auto-send (architectural invariant)
7. Fake provider default (no API key needed for CI)
8. Provider identity in trace

### 4. Wrapper Pattern for Backward Compatibility

DraftGenerationResult is a wrapper around DraftReply, not an extension. This preserves all 194 existing DraftReply tests unchanged. The guard_result lives on the wrapper, keeping DraftReply schema stable.

## Key Metrics

| Metric | Value | Significance |
|--------|-------|-------------|
| Citation Precision Avg | 1.0 | All cited evidence IDs are valid (10-case smoke test) |
| Evidence Coverage Avg | 0.30 | 30% of available evidence cited per case |
| Unsupported Claim Rate | 0.4 | 40% of cases have uncited substantive claims |
| Forbidden Promise Rate | 0.1 | 10% of cases contain detectable forbidden promises |
| Safe Fallback Rate | 0.0 | No cases triggered no-evidence fallback |
| Human Review Trigger Accuracy | 0.6 | 60% of cases have correct human review triggers |
| Citation Validation Pass Rate | 0.6 | 60% of cases pass structural citation validation |
| Claim Guard Pass Rate | 0.0 | 0% of cases pass full claim guard (expected — FakeLLMProvider limitations) |
| Average Confidence | 0.017 | Very low — reflects FakeLLMProvider's confidence scoring |

**Note**: 10-case smoke test using FakeLLMProvider. FakeLLMProvider tests workflow mechanics, not real LLM semantic quality. These numbers reflect the fake provider's behavior, not production performance.

## Component Map

```
DraftGenerationResult (wrapper)
  ├─ draft: DraftReply
  │    ├─ draft_text, provider_id, escalation_reason
  │    ├─ safety_notes, cited_evidence_ids
  │    └─ must_human_review (never downgrades)
  ├─ provider_name, model_name
  ├─ citation_validation: DraftCitationValidationResult
  │    ├─ is_valid, valid_cited_evidence_ids
  │    ├─ invalid_cited_evidence_ids, missing_citation_required
  │    └─ must_human_review (upgrades on failure)
  ├─ guard_result: GuardResult
  │    ├─ citation_coverage, has_uncited_claims
  │    ├─ has_forbidden_promise, evidence_sufficiency
  │    ├─ risk_flags_respected, guard_passed
  │    └─ escalation_reason (set on failure)
  └─ ticket_output: TicketOutput (for evaluation access)

generate_draft() pipeline:
  1. build_prompt_input() from TicketOutput
  2. call LLM provider (default: FakeLLMProvider)
  3. CitationValidator (content-level [N] checks)
  4. draft_citation_validator (structural ID checks)
  5. claim_guard (content-level checks)
  6. human review propagation (never downgrades)
  7. escalation_reason on guard failure
```

## Product Interpretation

### What This Means

**The draft generation pipeline is structured for safety, not just quality.** Each component serves a distinct safety function:

- **Prompt builder** constrains LLM input to retrieved evidence only
- **Citation validator** checks that cited IDs actually exist in the evidence candidates
- **Claim guard** detects uncited substantive claims and forbidden promises
- **Human review propagation** ensures high-risk and uncertain cases reach a human reviewer

For a product manager evaluating this system:

- **Citation precision = 100%** means the system never cites non-existent evidence IDs. This is foundational for trust.
- **Claim guard pass rate = 0%** with FakeLLMProvider is expected — the fake provider doesn't have semantic understanding to avoid forbidden promises. Real LLM integration is needed to test this.
- **Evidence coverage = 30%** means the system cites only a third of available evidence. This is a quality signal: not all retrieved evidence is relevant to the draft.

### Three Questions for Product

1. **Should we trust the draft generation pipeline?** Yes, at the structural level. Citation validation works, human review propagation is enforced, no-auto-send is maintained. The system is safe even if the LLM isn't perfectly grounded.

2. **Should we integrate a real LLM provider?** Yes — FakeLLMProvider validates workflow mechanics but not semantic quality. Real LLM integration is needed to test claim guard pass rates and evidence coverage.

3. **Is Phase 11 ready for portfolio evaluation?** Yes — the pipeline demonstrates systematic safety architecture with clear, quantified boundaries.

## Engineering Interpretation

### Architecture Takeaways

1. **Safety is layered, not centralized.** Each layer has a distinct responsibility: prompt builder (input), citation validator (evidence IDs), claim guard (claim quality), human review propagation (decision gate). Failure in one layer is caught before it propagates.

2. **Deterministic metrics enable offline evaluation.** All metrics in draft_metrics.py are pure functions with no network calls. This enables systematic evaluation without real LLM API costs.

3. **None-aware averaging prevents misleading aggregates.** Citation precision and evidence coverage return None when no citations/evidence exist. These None values are excluded from averages to avoid penalizing cases where the absence is legitimate (no evidence retrieved → fallback mode).

4. **Wrapper pattern preserves backward compatibility.** Adding DraftGenerationResult as a wrapper (not extending DraftReply) kept all existing DraftReply tests passing. The guard_result lives on the wrapper, not the schema.

5. **Fake provider default enables CI without API keys.** Like FakeEmbeddingProvider, FakeLLMProvider ensures the pipeline runs in CI without external dependencies. Real provider integration is opt-in only.

### What Not to Change

| Decision | Why Not |
|----------|---------|
| FakeLLMProvider as default | Tests workflow mechanics, not semantic quality; no API keys needed |
| Citation validation layer | Validates structural correctness of evidence IDs, not claim semantics |
| Claim guard as rule-based | Deterministic and testable; semantic claim detection deferred to future work |
| Wrapper over extension | Preserves backward compatibility with all DraftReply tests |
| Human review propagation as one-way | Never downgrades must_human_review; safety over flexibility |

## Boundaries

This is a **local demo / portfolio prototype** with the following constraints:

- **FakeLLMProvider only in current implementation** — tests workflow mechanics, not real LLM semantic quality
- **No real LLM API calls** — all evaluation uses deterministic fake provider
- **No network access required** — pipeline runs offline
- **No auto-send capability** — all drafts require human review or manual approval
- **Human-in-the-loop** — HIGH risk or uncertain cases force human review; this is architectural, not configurable
- **Not a production benchmark** — metrics are directional and demonstrate safety architecture, not LLM generation quality
- **Synthetic data only** — all tickets and knowledge records are synthetic
- **Single developer** — all infrastructure, evaluation, diagnosis, and reporting built by one person

## Resume Bullet (Chinese)

### 技术方案

> 主导 TicketPilot Phase 11 证据约束 LLM 草稿生成阶段，构建从 LLM provider 抽象到离线评估的完整安全架构。

> - 设计 LLMProvider ABC 接口 + FakeLLMProvider 实现（确定性、无网络、无 API 依赖），与 FakeEmbeddingProvider 模式一致，确保 CI 无外部依赖
> - 实现 Evidence-grounded prompt builder：将证据候选项 + 工单上下文转化为结构化 prompt，含证据约束 + 8 条安全规则 + 输出格式规范
> - 实现 DraftCitationValidationResult 和 validate_draft_citations()：验证 DraftReply.cited_evidence_ids 与证据候选项的 ID 一致性，检测重复和无效 ID
> - 实现 ClaimGuard（5 层检查）：声明覆盖率（解析 [N] 引用）、无证据声明检测、禁止承诺检测（9 种正则模式）、证据充足性、风险感知检查
> - 设计 generate_draft() 管线串联 prompt builder → LLM provider → CitationValidator → claim_guard → human review propagation
> - 实现离线草稿评估指标：8 项确定性指标（引用精确度、证据覆盖率、无声明率等），纯函数无网络调用

### 产品 / 评估

> 构建 AI 草稿生成的安全约束体系：从证据约束 prompt 到声明校验到人工审核传播，确保草稿质量可评测、高风险案例有人审兜底。

> - 定义 8 层安全架构：prompt 约束 → 引用验证 → ClaimGuard → 风险感知 → 人审传播 → no-auto-send → fake 默认 → provider 追踪
> - 设计 None-aware 平均值聚合：引用精确度和证据覆盖率在无引用/证据时返回 None，排除出平均值，避免误导性低值
> - Wrapper 模式保后向兼容：DraftGenerationResult 为 DraftReply 的 wrapper 而非扩展，所有 194 个 DraftReply 测试保持通过

## 1-Minute Interview Version

**Q: What did Phase 11 accomplish?**

Phase 11 added evidence-grounded draft generation to TicketPilot. The key insight was that LLM output should be constrained by retrieved evidence — not just instructed to use evidence, but structurally validated.

We built a pipeline where the prompt builder packs evidence candidates into the prompt with explicit citation markers. After generation, the citation validator checks that cited evidence IDs actually exist. The claim guard then scans for uncited substantive claims and forbidden promises. High-risk or uncertain cases force human review.

Everything is deterministic — FakeLLMProvider tests workflow mechanics without API keys or network calls. Real LLM integration is opt-in.

The architecture demonstrates safety-first design: each component has a distinct safety layer, failures don't propagate, and human review is the final gate.

**Q: What makes this different from a standard RAG?**

Standard RAG retrieves documents and passes them to an LLM with no constraint on output. TicketPilot's draft generation has five validation layers between retrieval and human review:

- Evidence-grounded prompt builder constrains input
- Citation validator validates evidence IDs
- Claim guard detects uncited claims and forbidden promises
- Human review propagation never downgrades must_human_review
- No-auto-send is an architectural invariant

This isn't about making the draft better — it's about making it safer and more auditable.

## 3-Minute Interview Version

**Q: Walk me through Phase 11.**

**The problem**: Phase 10 confirmed that retrieval quality is good (Doc-ID Recall@10 = 91.9%). The next frontier is generating draft replies grounded in that evidence. But LLM output is unconstrained — it can make up policy claims, cite non-existent evidence, or promise things the company can't deliver.

**The approach**: I built a pipeline with five validation layers between retrieval and human review. The design principle: safety is layered, not centralized.

1. **LLM Provider interface** (11.2): Like FakeEmbeddingProvider for retrieval, FakeLLMProvider is the default for draft generation. No API keys, no network calls. The interface is clean: `generate_draft(ticket_output, evidence_candidates) → DraftReply`.

2. **Evidence-grounded prompt builder** (11.3): Converts evidence candidates and ticket context into a structured prompt. Evidence is sorted by rank, truncated at 200 chars, packed with explicit citation markers. Eight safety rules in the system prompt: draft-only language, citation requirement, forbidden promises, risk-flag awareness.

3. **Citation validator extension** (11.4): Existing CitationValidator checked content-level [N] markers. I added DraftCitationValidationResult to check that cited_evidence_ids actually exist in the provided evidence candidates. Structural check vs content check — complementary layers.

4. **Claim guard** (11.5): Detects uncited substantive claims (substantive text without [N] markers), forbidden promises (9 regex patterns for amounts, legal terms, liability), and risk-aware violations (high-risk flags not acknowledged). This is rule-based and deterministic — no semantic analysis.

5. **Pipeline integration** (11.6): `generate_draft()` wires all components in sequence: build prompt → call provider → citation validation → claim guard → human review propagation. DraftGenerationResult is a wrapper around DraftReply, preserving all 194 existing tests.

6. **Human review console update** (11.7): Extended ReviewDecision with 15 audit fields (provider_name, citation_validation_valid, guard_passed, etc.). Streamlit display shows guard status, forbidden promise errors, uncited claim warnings. Reviewer remains final decision-maker.

7. **Offline draft evaluation** (11.8): Eight deterministic metrics computed from per-case DraftEvaluationRows. No network calls, no API keys. Markdown report includes scope boundaries and metric definitions.

**The results**:

- Citation precision = 100% (on 10-case smoke test — all cited IDs are valid)
- Claim guard pass rate = 0% (expected — FakeLLMProvider lacks semantic understanding)
- All components are deterministic and testable

**Why it matters**: Phase 11 demonstrates safety-first architecture for LLM-assisted workflow. Each validation layer has a distinct purpose, failures don't propagate, and human review is the final gate. The system is safe even if the LLM isn't perfectly grounded.

## Next Phase Options

### Recommended: Phase 11.9 — Portfolio Snapshot (this batch)

Phase 11's evidence chain is complete:
- LLM provider abstraction: **built and tested**
- Evidence-grounded prompt builder: **built and tested**
- ClaimGuard: **built and tested**
- Pipeline integration: **built and tested**
- Human review console update: **built and tested**
- Offline draft evaluation: **built and tested**

The next action is to document the Phase 11 snapshot and update portfolio materials with Phase 11 references.

### P1: Real LLM Provider Integration

With the pipeline validated and all components tested, the natural next step is to integrate a real LLM provider (e.g., Claude API via OpenAI-compatible endpoint). This would enable:
- Real semantic claim quality evaluation
- Evidence coverage optimization
- Forbidden promise rate reduction

### P2: Query Expansion Audit (from Phase 10)

The 7 zero-hit cases identified in Phase 10's diagnosis are query expansion candidates. Audit query terms against knowledge record terms to determine whether underspecification or term mismatch is the cause.

### P3: Fusion Ranking Optimization (from Phase 10)

The 32 partial-hit cases identified in Phase 10 are fusion ranking candidates. Experiment with lower RRF k, score-based fusion, or conditional weighting.

## Files Reference

| File | Purpose |
|------|---------|
| `docs/portfolio/phase11_evidence_draft_snapshot.md` | This file |
| `docs/portfolio/ticketpilot_product_case_onepager.md` | Product case one-pager (Phase 11 summary) |
| `docs/portfolio/product_portfolio_material_pack.md` | Portfolio material pack (Phase 11 references) |
| `src/ticketpilot/drafting/llm_provider.py` | LLM provider interface + FakeLLMProvider |
| `src/ticketpilot/drafting/prompt_builder.py` | Evidence-grounded prompt builder |
| `src/ticketpilot/drafting/draft_citation_validator.py` | Citation validation for DraftReply |
| `src/ticketpilot/drafting/claim_guard.py` | ClaimGuard with 5 checks |
| `src/ticketpilot/drafting/generator.py` | DraftGenerationResult + generate_draft() |
| `src/ticketpilot/evaluation/draft_metrics.py` | 8 deterministic metrics |
| `scripts/run_draft_evaluation.py` | CLI runner for offline evaluation |
| `reports/eval/phase11_draft_evaluation_report.md` | Smoke test results |
| `openspec/changes/add-evidence-grounded-llm-draft/tasks.md` | OpenSpec tasks with completion status |