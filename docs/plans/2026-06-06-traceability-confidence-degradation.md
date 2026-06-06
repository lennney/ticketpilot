# TicketPilot 追溯 + Eval + 置信度 + 降级机制 实施计划

> 日期: 2026-06-06
> 目标: 完善 TicketPilot 的可观测性和质量保障体系
> 约束: 保持 deterministic（no LLM in pipeline），OpenSpec workflow
> 状态: Plan Review v2 — 已修复审查发现的 4 critical + 3 high 问题

---

## 概述

4 个模块，按依赖关系排序：

```
Task 1: 全链路追溯 → 基础设施，其他模块都依赖它
Task 2: 多维置信度 → 依赖追溯数据，统一现有 ConfidenceGuard
Task 3: 分级降级机制 → 依赖置信度分数
Task 4: Eval Pipeline 完善 → 验证以上所有模块
```

### ⚠️ 前置条件：OpenSpec Change

按 AGENTS.md §7，本次修改涉及核心 pipeline，需先创建 OpenSpec change：

```
openspec/changes/traceability-confidence-degradation/
├── proposal.md    # 变更提案
├── design.md      # 技术设计
├── tasks.md       # 任务清单
└── specs/         # 规格说明
```

---

## Task 1: 全链路追溯 (Full-Chain Traceability)

**现状**: `retrieval/traces.py` 有完整的检索追溯 schema（KeywordResult, VectorResult, FusedResult），`tracing/__init__.py` 有 AgentTrace/StepTrace。但两者没有连接，且缺少"答案→引用→chunk"的反向追溯。

**目标**: 每条客服回复都能回答"这句话来自哪个知识文档的哪个段落"。

### 1.1 创建 `src/ticketpilot/tracing/provenance.py`

新增 Provenance（溯源）数据结构，连接检索 trace 和生成 trace。

**⚠️ 设计决策：**
- 使用 **Pydantic BaseModel**（与项目所有现有 schema 一致，不用 @dataclass）
- chunk_id/doc_id 使用 **UUID** 类型（与 FusedResult、Citation 一致）
- Provenance 是 `DraftReply` 的可选扩展字段，**不改变现有返回类型**

```python
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

class ClaimProvenance(BaseModel):
    """单条声明的溯源信息"""
    claim_text: str                    # 回复中的声明文本
    citation_index: int                # [N] 引用编号
    source_chunk_id: UUID              # 知识库 chunk UUID (与 FusedResult.chunk_id 一致)
    source_doc_id: UUID                # 来源文档 UUID (与 FusedResult.doc_id 一致)
    source_doc_type: str               # faq / policy / case (与 DocType 一致)
    retrieval_method: str              # keyword / vector / fused
    retrieval_score: float             # 检索分数 (RRF or raw)
    confidence: float                  # 追溯置信度 (0-1)

class ResponseProvenance(BaseModel):
    """整条回复的完整溯源"""
    response_id: str
    ticket_id: str
    claims: list[ClaimProvenance]
    overall_confidence: float
    generated_at: datetime
```

**与现有 DraftGenerationTrace 的关系：**
- `DraftGenerationTrace`（schemas.py）记录生成过程（template_used, fill_rate）
- `ResponseProvenance` 记录溯源链（每条 claim 来自哪个 chunk）
- 两者互补，不冲突。Provenance 作为 DraftReply 的新可选字段。

**TDD：先写测试**
```bash
# 先写测试
touch tests/unit/test_provenance.py
# 测试内容：ClaimProvenance 创建、序列化、字段验证
# 验证：python -m pytest tests/unit/test_provenance.py -v
# 预期：FAIL (模块不存在)
# 再写实现
touch src/ticketpilot/tracing/provenance.py
# 验证：python -m pytest tests/unit/test_provenance.py -v
# 预期：PASS
```

**文件**: `src/ticketpilot/tracing/provenance.py` (~80 行)
**测试**: `tests/unit/test_provenance.py` (~60 行)

### 1.2 修改 `drafting/schemas.py` — DraftReply 增加可选 provenance 字段

**⚠️ 向后兼容：** 添加 `provenance: Optional[ResponseProvenance] = None`，默认 None，不破坏任何现有调用方。

```python
# 在 DraftReply 中新增：
from ticketpilot.tracing.provenance import ResponseProvenance

class DraftReply(BaseModel):
    ...  # 现有字段全部保留
    provenance: Optional[ResponseProvenance] = Field(
        default=None,
        description="Full-chain provenance for the draft reply"
    )
```

修改 `drafting/generate.py`：在 `generate_draft()` 中，如果有 retrieval_trace，自动构建 provenance。

**TDD：先写测试**
```bash
# 测试 DraftReply 可以不带 provenance 创建（向后兼容）
# 测试 DraftReply 可以带 provenance 创建
# 测试 generate_draft() 返回的 DraftReply 包含 provenance
# 验证：python -m pytest tests/unit/test_generate_provenance.py -v
```

**文件**: 修改 `src/ticketpilot/drafting/schemas.py` + `src/ticketpilot/drafting/generate.py`
**测试**: `tests/unit/test_generate_provenance.py` (~80 行)

### 1.3 创建 Provenance 查询 API

```python
class ProvenanceStore:
    """Provenance 持久化和查询（内存版，demo 用）"""
    def store(self, provenance: ResponseProvenance) -> None: ...
    def get_by_response(self, response_id: str) -> Optional[ResponseProvenance]: ...
    def get_by_chunk(self, chunk_id: UUID) -> list[ResponseProvenance]: ...
```

**⚠️ 砍掉 `get_by_doc()`** — 审查认为 YAGNI，demo 项目不需要。

**TDD：先写测试**
```bash
touch tests/unit/test_provenance_store.py
# 测试 store + get_by_response + get_by_chunk
# 验证：python -m pytest tests/unit/test_provenance_store.py -v
```

**文件**: `src/ticketpilot/tracing/store.py` (~80 行)
**测试**: `tests/unit/test_provenance_store.py` (~50 行)

---

## Task 2: 多维置信度评分 (Multi-Dimensional Confidence)

**现状分析 — 三套置信度系统：**

| 系统 | 位置 | 阈值 | 用途 |
|------|------|------|------|
| `DraftReply.confidence` + `confidence_level` | drafting/schemas.py | HIGH=0.8, MEDIUM=0.6 | 生成时的置信度 |
| `ConfidenceGuard` | guardrails/__init__.py | HIGH=0.8, MEDIUM=0.6, LOW=0.4 | Guardrail 检查 |
| 分类器 `confidence` | classification/classifier.py | 0.7 (单一阈值) | 分类置信度 |

**⚠️ 设计决策：统一，不重复**

新的 `ConfidenceScorer` **替代** 现有的 `ConfidenceGuard`，并**填充** `DraftReply.confidence` 和 `confidence_level`。具体做法：

1. `ConfidenceScorer` 计算多维置信度 → 返回 `ConfidenceBreakdown`
2. `ConfidenceBreakdown.overall` 填入 `DraftReply.confidence`
3. `ConfidenceBreakdown.level` 填入 `DraftReply.confidence_level`
4. 旧的 `ConfidenceGuard` 标记为 deprecated，内部委托给 `ConfidenceScorer`

**阈值统一为：**
```python
THRESHOLDS = {
    "high": 0.8,     # 与现有一致
    "medium": 0.6,   # 与现有一致（不改为 0.5）
    "low": 0.4,      # 与现有一致（不改为 0.3）
}
```

### 2.1 创建 `src/ticketpilot/confidence/scorer.py`

```python
from enum import Enum
from pydantic import BaseModel, Field
from uuid import UUID

class ConfidenceLevel(str, Enum):
    HIGH = "high"         # ≥ 0.8 → 直接回答（进人工审核）
    MEDIUM = "medium"     # ≥ 0.6 → 回答 + 免责声明（进人工审核）
    LOW = "low"           # ≥ 0.4 → 部分回答 + 建议转人工（进人工审核）
    CRITICAL = "critical" # < 0.4 → 直接转人工，不生成回复草稿

class ConfidenceBreakdown(BaseModel):
    """置信度分解"""
    retrieval_confidence: float = Field(ge=0, le=1)
    classification_confidence: float = Field(ge=0, le=1)
    citation_confidence: float = Field(ge=0, le=1)
    evidence_density: float = Field(ge=0, le=1)
    overall: float = Field(ge=0, le=1)
    level: ConfidenceLevel

class ConfidenceScorer:
    WEIGHTS = {
        "retrieval": 0.35,
        "classification": 0.25,
        "citation": 0.25,
        "evidence_density": 0.15,
    }
    
    # expected_chunks: 按 intent 类型配置
    EXPECTED_CHUNKS = {
        "refund": 3,      # 退款类通常需要政策+案例+FAQ
        "shipping": 2,    # 物流类通常需要FAQ+政策
        "complaint": 3,   # 投诉类需要政策+案例+流程
        "inquiry": 2,     # 咨询类需要FAQ+产品信息
        "other": 2,       # 默认
    }
    
    def score(self, ticket_output: TicketOutput, draft: Optional[DraftReply] = None) -> ConfidenceBreakdown:
        """
        计算多维置信度。
        
        Args:
            ticket_output: pipeline 输出（含 classification + retrieval_trace）
            draft: 可选，如果有 draft 则计算 citation_confidence
        """
        ...
```

**TDD：先写测试**
```bash
touch tests/unit/test_confidence_scorer.py
# 测试：高置信场景、低置信场景、边界值、权重计算
# 验证：python -m pytest tests/unit/test_confidence_scorer.py -v
```

**文件**: `src/ticketpilot/confidence/scorer.py` (~130 行) + `src/ticketpilot/confidence/__init__.py`
**测试**: `tests/unit/test_confidence_scorer.py` (~100 行)

### 2.2 ~~Calibrator~~ → 延后到 Task 4 之后

**审查认为**：Calibrator 需要 eval 数据，而 eval 在 Task 4。延后到 Task 4 完成后作为 follow-up。

---

## Task 3: 分级降级机制 (Tiered Degradation)

**现状**: `pipeline.py` 的 try/except 降级到默认值（intent=OTHER, confidence=0.5）。没有分级策略。

**目标**: 根据置信度分数，走不同的降级路径。

### 3.1 创建 `src/ticketpilot/degradation/strategy.py`

```python
from enum import Enum
from pydantic import BaseModel
from typing import Optional
from ticketpilot.confidence.scorer import ConfidenceBreakdown

class ResponseStrategy(str, Enum):
    """回复策略 — 按置信度分级，高置信自动发送，低置信进人工"""
    AUTO_SEND = "auto_send"               # 高置信 (≥0.8)：自动发送
    AUTO_SEND_CAUTIOUS = "auto_send_cautious"  # 中置信 (≥0.6)：自动发送 + 免责声明
    HUMAN_REVIEW = "human_review"         # 低置信 (≥0.4)：进人工审核后再发
    HUMAN_ESCALATION = "human_escalation" # 极低置信 (<0.4)：直接转人工，不生成草稿

class DegradedResponse(BaseModel):
    """降级后的响应"""
    strategy: ResponseStrategy
    answer: Optional[str] = None          # 回复文本（HUMAN_ESCALATION 时为 None）
    confidence: ConfidenceBreakdown
    human_handoff_context: Optional[dict] = None  # 转人工上下文
    disclaimer: Optional[str] = None      # 免责声明
    escalation_reason: Optional[str] = None

class DegradationRouter:
    """根据置信度选择回复策略
    
    分级策略：
    - HIGH (≥0.8): 自动发送，后台抽检
    - MEDIUM (≥0.6): 自动发送 + 免责声明
    - LOW (≥0.4): 进人工审核，附带置信度分析
    - CRITICAL (<0.4): 直接转人工，不生成草稿
    """
    
    DISCLAIMER = "以上回答基于知识库检索，仅供参考。如需进一步帮助，请转接人工客服。"
    
    def route(self, confidence: ConfidenceBreakdown, draft: Optional[str] = None) -> DegradedResponse:
        if confidence.level == ConfidenceLevel.HIGH:
            return DegradedResponse(
                strategy=ResponseStrategy.AUTO_SEND,
                answer=draft,
                confidence=confidence,
            )
        elif confidence.level == ConfidenceLevel.MEDIUM:
            return DegradedResponse(
                strategy=ResponseStrategy.AUTO_SEND_CAUTIOUS,
                answer=draft,
                confidence=confidence,
                disclaimer=self.DISCLAIMER,
            )
        elif confidence.level == ConfidenceLevel.LOW:
            return DegradedResponse(
                strategy=ResponseStrategy.HUMAN_REVIEW,
                answer=draft,
                confidence=confidence,
                disclaimer="置信度较低，已提交人工审核。",
                escalation_reason=f"置信度过低 (overall={confidence.overall:.2f})",
            )
        else:  # CRITICAL
            return DegradedResponse(
                strategy=ResponseStrategy.HUMAN_ESCALATION,
                answer=None,
                confidence=confidence,
                human_handoff_context=self._build_handoff_context(confidence, draft),
                escalation_reason=f"置信度极低 (overall={confidence.overall:.2f})，自动生成不可靠",
            )
    
    def _extract_cited_claims(self, draft: str) -> str:
        """只保留有 [N] 引用标记的句子"""
        ...
    
    def _build_handoff_context(self, confidence: ConfidenceBreakdown, draft: Optional[str]) -> dict:
        """构建转人工上下文（Warm Handoff）"""
        return {
            "confidence_breakdown": confidence.model_dump(),
            "attempted_draft": draft,
            "escalation_reason": confidence.level.value,
            # pipeline 上下文由调用方注入
        }
```

**TDD：先写测试**
```bash
touch tests/unit/test_degradation.py
# 测试：4 种策略路由、免责文案、转人工上下文、_extract_cited_claims
# 验证：python -m pytest tests/unit/test_degradation.py -v
```

**文件**: `src/ticketpilot/degradation/strategy.py` (~180 行) + `src/ticketpilot/degradation/__init__.py`
**测试**: `tests/unit/test_degradation.py` (~120 行)

### 3.2 修改 `pipeline.py` — 集成置信度 + 降级路由

在 pipeline 的最后阶段（evidence retrieval 之后），加入：
1. `ConfidenceScorer.score()` 计算多维置信度
2. 将置信度填入 `DraftReply.confidence` 和 `confidence_level`
3. `DegradationRouter.route()` 选择策略
4. 输出增加 `DegradedResponse`

**⚠️ 向后兼容：** `intake_risk_pipeline()` 返回类型不变（TicketOutput），新增 `degraded_response` 字段：

```python
class TicketOutput(BaseModel):
    ...  # 现有字段
    degraded_response: Optional[DegradedResponse] = None  # 新增
```

**TDD：先写测试**
```bash
# 测试 pipeline 在不同置信度下产出正确的 DegradedResponse
# 验证：python -m pytest tests/unit/test_pipeline_degradation.py -v
```

**文件**: 修改 `src/ticketpilot/pipeline.py` + `src/ticketpilot/schema/ticket.py`
**测试**: `tests/unit/test_pipeline_degradation.py` (~80 行)

### 3.3 ~~Circuit Breaker~~ → 砍掉

**审查认为**：Demo/Portfolio 项目没有生产流量，熔断器 YAGNI。如果未来上生产再加。

---

## Task 4: Eval Pipeline 完善

### 4.1 确认现有 Eval Pipeline 可运行

```bash
# 先确认数据库可用
docker compose up -d
# 确认 seed 数据
uv run python -c "from ticketpilot.retrieval.db.seeding import seed_knowledge_chunks; seed_knowledge_chunks(clear_existing=True)"
# 跑 eval
uv run python scripts/run_eval.py 2>&1
# 预期：输出 evaluation_report.json，包含 101 条结果

uv run python scripts/run_agent_eval.py 2>&1
# 预期：输出 agent eval 结果
```

**如果有运行时错误**：记录具体错误，修复后重跑。不猜测。

### 4.2 增加追溯 + 置信度的 Eval 指标

在 `agent_eval.py` 的 EvalResult 中新增：

```python
class EvalResult:
    ...  # 现有字段
    provenance_coverage: float = 0.0    # 有溯源的 claims / 总 claims
    confidence_level: str = "unknown"   # HIGH/MEDIUM/LOW/CRITICAL
```

### 4.3 创建 Eval 回归对比脚本

```python
# scripts/compare_eval_reports.py
# 对比两次 eval 结果，任何指标下降 >5% 则 exit 1

def compare(baseline_path: str, current_path: str, threshold: float = 0.05) -> bool:
    ...
```

```bash
# scripts/run_eval_gate.sh
uv run python scripts/run_eval.py --output reports/eval/current.json
uv run python scripts/compare_eval_reports.py \
    --baseline reports/eval/baseline.json \
    --current reports/eval/current.json \
    --threshold 0.05
# 预期：PASS (exit 0) 或 FAIL (exit 1 + 报告哪些指标下降)
```

**TDD：先写测试**
```bash
touch tests/unit/test_eval_comparison.py
# 测试：baseline vs current 对比、下降检测、阈值触发
# 验证：python -m pytest tests/unit/test_eval_comparison.py -v
```

**文件**: `scripts/compare_eval_reports.py` (~100 行) + `scripts/run_eval_gate.sh` (~20 行)
**测试**: `tests/unit/test_eval_comparison.py` (~60 行)

### 4.4 Calibrator（延后到此步）

现在有 eval 数据了，可以实现 `ConfidenceCalibrator`：

```python
# src/ticketpilot/confidence/calibrator.py
class ConfidenceCalibrator:
    """用 eval 结果校准置信度阈值"""
    def calibrate(self, eval_results: list[EvalResult]) -> CalibrationReport: ...
```

**文件**: `src/ticketpilot/confidence/calibrator.py` (~80 行)
**测试**: `tests/unit/test_calibrator.py` (~50 行)

---

## 依赖关系

```
OpenSpec change 创建 (前置)
  ↓
Task 1.1 (Provenance schema)     ← TDD: test first
  ↓
Task 1.2 (DraftReply + provenance) ← TDD: test first
  ↓
Task 1.3 (Provenance store)       ← TDD: test first
  ↓
Task 2.1 (Confidence scorer)      ← TDD: test first, 替代 ConfidenceGuard
  ↓
Task 3.1 (Degradation strategy)   ← TDD: test first
  ↓
Task 3.2 (Pipeline integration)   ← TDD: test first
  ↓
Task 4.1 (Eval pipeline 确认)
  ↓
Task 4.2 (新增 eval 指标)
  ↓
Task 4.3 (Eval 回归对比)
  ↓
Task 4.4 (Calibrator)
  ↓
Quality Gate: uv run bash scripts/run_quality_gate.sh
```

## 预估工作量

| Task | 新增文件 | 修改文件 | 测试文件 | 预估行数 |
|------|---------|---------|---------|---------|
| 1.1 Provenance schema | 1 | 0 | 1 | ~140 |
| 1.2 DraftReply integration | 0 | 2 | 1 | ~130 |
| 1.3 Provenance store | 1 | 0 | 1 | ~130 |
| 2.1 Confidence scorer | 2 (__init__) | 0 | 1 | ~230 |
| 3.1 Degradation strategy | 2 (__init__) | 0 | 1 | ~300 |
| 3.2 Pipeline integration | 0 | 2 | 1 | ~130 |
| 4.1-4.3 Eval pipeline | 1 | 1 | 1 | ~180 |
| 4.4 Calibrator | 1 | 0 | 1 | ~130 |
| **合计** | **8 新文件** | **5 修改** | **8 测试** | **~1370 行** |

## 每个 Task 的验证命令

| Task | 验证命令 | 预期输出 |
|------|---------|---------|
| 1.1 | `uv run python -m pytest tests/unit/test_provenance.py -v` | PASS |
| 1.2 | `uv run python -m pytest tests/unit/test_generate_provenance.py -v` | PASS |
| 1.3 | `uv run python -m pytest tests/unit/test_provenance_store.py -v` | PASS |
| 2.1 | `uv run python -m pytest tests/unit/test_confidence_scorer.py -v` | PASS |
| 3.1 | `uv run python -m pytest tests/unit/test_degradation.py -v` | PASS |
| 3.2 | `uv run python -m pytest tests/unit/test_pipeline_degradation.py -v` | PASS |
| 4.1 | `uv run python scripts/run_eval.py` | evaluation_report.json |
| 4.2-4.3 | `uv run python -m pytest tests/unit/test_eval_comparison.py -v` | PASS |
| 4.4 | `uv run python -m pytest tests/unit/test_calibrator.py -v` | PASS |
| **最终** | `uv run bash scripts/run_quality_gate.sh` | ALL PASSED |

## 验收标准

1. **追溯**: 每条回复都能通过 `ProvenanceStore.get_by_response()` 查到完整溯源链
2. **置信度**: `ConfidenceScorer.score()` 返回 4 维 breakdown，阈值与现有系统一致（0.8/0.6/0.4）
3. **降级**: HIGH/MEDIUM 自动发送，LOW 进人工审核，CRITICAL 直接转人工
4. **Eval**: 现有 101 条 eval tickets 全部通过，新增指标有 baseline
5. **测试**: 所有新模块有单元测试，覆盖率 ≥ 70%
6. **Quality Gate**: `scripts/run_quality_gate.sh` 全部通过
7. **向后兼容**: 现有 API 调用方不受影响（所有新字段 Optional + 默认值）
8. **AGENTS.md 更新**: "No auto-send" 改为分级发送策略
