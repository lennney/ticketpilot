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
Phase 15.4（Chat UI 集成）+ 技术债整理

## Active OpenSpec
- `align-chat-support-product-experience`（Phase 15）
- `address-technical-debt`（技术债修复）

## tasks.md 位置
- Phase 15: openspec/changes/align-chat-support-product-experience/tasks.md
- Tech debt: openspec/changes/address-technical-debt/tasks.md

## 技术栈
- Python 3.11 / uv
- PostgreSQL + pgvector
- pytest + ruff

## 下一步任务
A1: RetrievalTrace class collision fix（traces.py vs schema/retrieval.py）
然后 commit 并 push

## 技术债优先级
P1: A1（RetrievalTrace冲突）
P2: A2 ✅（ARCHITECTURE.md同步：更新opt-in LLM/embedding描述、添加Phase15 Chat模块）、B1 ✅（claim_guard映射错误）、B2 ✅（_build_prompt_input丢弃）、B3 ✅（safe-fallback重复）
P3: C1（METRICS过时）

## 当前技术债 OpenSpec
`address-technical-debt` — 查看 tasks.md 获取详细任务列表