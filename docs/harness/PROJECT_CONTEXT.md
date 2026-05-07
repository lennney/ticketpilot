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
Phase 15.4: Streamlit 聊天界面集成（查看 align-chat-support-product-experience/tasks.md）
技术债整理：按 tasks.md 顺序修复（先 B2 → B3 → B1 → A2 → A1）

## 技术债优先级
P1: A1（RetrievalTrace冲突）、A2（ARCHITECTURE.md不同步）、B1（claim_guard映射错误）
P2: B2（_build_prompt_input丢弃）、B3（safe-fallback重复）
P3: C1（METRICS过时）、C2（ARCHITECTURE.md缺Phase15）

## 当前技术债 OpenSpec
`address-technical-debt` — 查看 tasks.md 获取详细任务列表