---
phase: 15.4 / tech-debt
change: align-chat-support-product-experience, address-technical-debt
last_updated: 2026-05-08
owner: controller
---

# TicketPilot — Project State

## 核心约束
- No auto-send
- No LLM in pipeline（default）
- Fake embedding default

## 当前阶段
Phase 15.4（Chat UI Risk Escalation Display）

## Active OpenSpec
- `align-chat-support-product-experience`（Phase 15）

## Phase Loop 状态
- [x] Step 1: Planner (project-director subagent) ✅
- [x] Step 2: Requirements Analysis (general-purpose subagent) ✅
- [x] Step 3: Implementation (backend-engineer subagent) ✅
- [x] Step 4: Review (code-reviewer subagent) ✅
- [x] Step 5: Doc Review (code-reviewer subagent) ✅ (2 issues fixed: tasks.md, ARCHITECTURE.md boundary)
- [x] Step 6: Experience Consolidation (general-purpose subagent) ✅
- [ ] Step 7: Controller Coordination (commit + push)

## 下一步任务
Phase 15.6: Human Review Queue Link (完整 loop)

## Phase Loop 规则 (更新)
- Requirements Analysis: 必须像产品经理一样详细，包含字段定义
- Skills/Learning: 错误/模式 → codify 到 skills/ 可复用
- Code Review 失败 → 进入 Fix Phase，不忽视

## 技术栈
- Python 3.11 / uv
- PostgreSQL + pgvector
- pytest + ruff

## 下一步任务
A1: RetrievalTrace class collision fix（traces.py vs schema/retrieval.py）
然后 commit 并 push

## 技术债优先级
P1: 全部完成 ✅
P2: -
P3: C1（METRICS过时）

## 当前技术债 OpenSpec
`address-technical-debt` — 查看 tasks.md 获取详细任务列表