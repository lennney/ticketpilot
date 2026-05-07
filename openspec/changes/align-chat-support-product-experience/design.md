# Design: Chat Support Product Experience

## 1. 端到端流程

```
用户输入消息
    │
    ▼
[Chat Input] 用户在 chat input 输入中文客服消息
    │
    ▼
Normalize Ticket
    │
    ▼
Intent Classification → issue_type（8 类）
    │
    ▼
Risk Assessment → risk_flags + severity
    │
    ▼
Evidence Retrieval → FAQ / Policy / Case 分层检索
    │
    ├─ LOW-risk + evidence sufficient → 生成草稿
    ├─ MEDIUM-risk → 生成草稿 + guard check
    └─ HIGH-risk / guard-fail / no evidence → 直接进入人工队列
    │
    ▼
Draft Generation（FakeLLMProvider，默认）
    │
    ▼
Citation Validation + Claim Guard
    │
    ├─ guard_pass=True → 展示 AI 草稿
    └─ guard_pass=False → 展示失败原因 + 人工介入
    │
    ▼
Human Review Queue
    │
    ├─ LOW-risk + guard-pass → 模拟"AI 回复已生成"（demo only）
    └─ HIGH-risk / guard-fail / no evidence → 进入人工审核
    │
    ▼
Review Console（已有）→ Approve / Edit / Escalate / Reject
```

### 关键决策点

- **no auto-send**：所有 AI 回复都是 demo 展示，不发送任何消息给任何人
- **human-in-the-loop**：高风险必然进人工，不存在绕过
- **evidence-grounded**：草稿必须引用知识库证据

## 2. 前台 Chat Demo UI（Streamlit）

### 布局

```
┌─────────────────────────────────────────────────────┐
│  TicketPilot AI 客服 Copilot（Local Demo）           │
├─────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────┐   │
│  │  [USER] 我要退款，订单号12345                 │   │
│  │  [AI]   已为您查询...                         │   │
│  │  [AI]   根据平台政策，7天内可申请退货[chunk]  │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  ┌──────────────┐ ┌────────────────────────────┐   │
│  │ 风险状态      │ │ 证据面板                   │   │
│  │ ● LOW        │ │ [chunk] 退货政策 v0.95     │   │
│  │ 无高风险标记  │ │ [chunk] 退换货流程 v0.88   │   │
│  │ ✓ 可生成草稿  │ │                            │   │
│  └──────────────┘ └────────────────────────────┘   │
│                                                     │
│  ┌──────────────────────────────────────────────┐   │
│  │ AI 客服回复草稿                                │   │
│  │ 尊敬的用户，根据政策[chunk_id]，您可以在签收后  │   │
│  │ 7天内申请退货...                               │   │
│  │ ✓ guard_passed                               │   │
│  └──────────────────────────────────────────────┘   │
│                                                     │
│  [Human Review Required] ← 仅在需要时显示            │
│  [进行人工审核] [编辑草稿] [直接通过]                │
│                                                     │
│  [请输入消息...]                    [发送]         │
└─────────────────────────────────────────────────────┘
```

### Chat 状态机

- `idle`：等待用户输入
- `processing`：AI 正在处理
- `draft_ready`：草稿已生成，等待人工确认
- `human_review`：需要人工审核
- `reviewed`：人工已决策

### 风险展示

| Severity | 颜色 | 含义 |
|---|---|---|
| LOW | 绿色 | 普通 FAQ / 售后咨询，草稿可直接展示 |
| MEDIUM | 黄色 | 有一定复杂度，建议人工确认 |
| HIGH | 红色 | 必须人工审核，不展示草稿 |

### 风险标记展示

```
risk_flags: [COMPENSATION_RISK, LEGAL_RISK]
→ "⚠️ 检测到赔偿风险、法律风险 → 必须人工处理"
```

## 3. Pipeline-to-Chat Adapter

### 目标

把现有 `TicketOutput` / `DraftGenerationResult` 适配到 chat UI 展示格式。

### 新增模块

```
src/ticketpilot/chat/
    __init__.py
    schemas.py      # ChatMessage, ChatSession, ChatState, ChatDisplay
    adapter.py     # ticket_output_to_chat() — pipeline output → chat display
    app.py         # Streamlit app（重构或新建）
```

### Schema

```python
class ChatMessage:
    role: Literal["user", "ai", "system"]
    text: str
    timestamp: datetime
    metadata: dict  # optional: evidence_ids, risk_flags, guard_result

class ChatSession:
    messages: list[ChatMessage]
    ticket_output: TicketOutput | None
    draft_result: DraftGenerationResult | None
    state: ChatState
    human_review_required: bool
    human_review_decision: ReviewDecision | None

class ChatState(str, Enum):
    IDLE = "IDLE"
    PROCESSING = "PROCESSING"
    DRAFT_READY = "DRAFT_READY"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    REVIEWED = "REVIEWED"

class ChatDisplay:
    """Formatted display data for chat UI."""
    user_message: str
    ai_message: str | None
    risk_badge: str  # "LOW" / "MEDIUM" / "HIGH"
    risk_flags: list[str]
    evidence_panel: list[EvidenceDisplayItem]
    draft_text: str | None
    guard_passed: bool | None
    guard_result: GuardResult | None
    human_review_required: bool
    escalation_reason: str | None
    citation_ids: list[str]
```

### Adapter 函数

```python
def ticket_output_to_chat_display(
    ticket_output: TicketOutput,
    draft_result: DraftGenerationResult | None = None,
) -> ChatDisplay:
    """Convert pipeline output to chat display format.

    Rules:
    - HIGH severity or guard_fail → human_review_required=True
    - MEDIUM severity + guard_pass → human_review_required=False
    - LOW severity + guard_pass → human_review_required=False
    - evidence must be grouped by type (FAQ/Policy/Case)
    - citation markers shown inline in draft
    """
    ...
```

## 4. 风险决策矩阵

| Severity | Evidence | Guard Pass | Action |
|---|---|---|---|
| LOW | 有 | True | 展示 AI 草稿 |
| LOW | 有 | False | 人工审核 |
| LOW | 无 | — | 人工审核 |
| MEDIUM | 有 | True | 人工确认 |
| MEDIUM | 有 | False | 人工审核 |
| MEDIUM | 无 | — | 人工审核 |
| HIGH | — | — | 人工审核 |

**原则：高风险永远人工审核，不管 guard 状态。**

## 5. Guard Taxonomy 的位置

Guard taxonomy 不是产品主线，而是安全底座。

### 已完成的 Phase 14.2–14.2.1

- `GuardFailureType` enum（8 types）
- `failure_reasons` 字段（failure-only）
- Safe fallback deferred

### 后续优先级

Phase 14.3–14.7（guard taxonomy 扩展）暂停，优先级低于 chat demo。
Phase 15.x（chat demo）优先。

### Guard 在 chat 中的展示

- `guard_pass=True` → 绿色 ✓，草稿可用
- `guard_pass=False` → 红色 ✗，展示 failure_reasons
- failure_reasons 作为 reviewer 的参考，不作为自动决策

## 6. 现有 Review Console 的复用

现有 Streamlit review console (`review/console.py`) 不废弃，而是作为人工客服接管台。

### 复用方式

- Chat demo 中点击"进行人工审核" → 跳转到 review console（或在 chat 中嵌入）
- Review console 已有：user message, issue_type, risk_flags, severity, evidence, draft, guard result
- 需要补充：chat session 历史（方便 reviewer 理解上下文）

### 兼容性

- `DraftGenerationResult` 已有完整字段
- `ReviewDecision` 已有 draft audit fields（Phase 11.7）
- adapter 层将 pipeline 输出转为 chat display 格式，review console 消费原始 `DraftGenerationResult`

## 7. Evidence Panel 展示

```
证据面板
├─ 政策类 (2)
│  ├─ [chunk_id] 退货政策 v0.95
│  └─ [chunk_id] 退换货流程 v0.88
├─ 案例类 (1)
│  └─ [chunk_id] 订单12345退货案例 v0.72
└─ FAQ类 (0)
    └─ （无相关FAQ）
```

每条证据显示：chunk_id（内联引用用）、标题、来源类型、相关度得分。

## 8. 与 Phase 14 的关系

### Phase 14 已完成

- 14.1: Planning（OpenSpec change created）
- 14.2: Guard taxonomy data model（committed c59604e）
- 14.2.1: Taxonomy cleanup（committed c59604e）

### Phase 14 暂停

- 14.3–14.7: Guard taxonomy extensions → 优先级低于 chat demo

### Phase 14 后续处理

Phase 15.x chat demo 完成后，可以恢复 Phase 14.3（safe language classifier）等工作。
Guard taxonomy 继续作为安全底座，但叙事优先级降低。

## 9. 技术约束

- **FakeLLMProvider**：默认不调用真实 LLM API
- **Deterministic**：同一输入永远产生相同输出
- **No auto-send**：草稿不发送任何消息
- **Human-in-the-loop**：高风险必然人工审核
- **Local only**：不需要网络访问（检索用 fake embedding）
