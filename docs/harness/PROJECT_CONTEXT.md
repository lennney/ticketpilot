---
phase: 15.8 complete
change: align-chat-support-product-experience, address-technical-debt (both archived)
last_updated: 2026-05-08
owner: controller
---

# TicketPilot — Project State

## 核心约束
- No auto-send
- No LLM in pipeline（default）
- Fake embedding default

## 当前阶段
Phase 15.8 完成 — Phase 15 全部收尾 ✅

## Active OpenSpec
- `align-chat-support-product-experience` ✅ 已归档 (2026-05-08-align-chat-support-product-experience)
- `address-technical-debt` ✅ 已归档 (2026-05-08-address-technical-debt)

## Phase 15 总结
- 15.1-15.8 全部完成
- Quality Gate: 1239 unit + 146 integration, 0 skip, 83% coverage ✅
- OpenSpec --all: 27 passed ✅
- Chat UI: Risk Display + Evidence Panel + Human Review Queue ✅
- Portfolio Docs: 已更新 Phase 15 narrative

## 技术栈
- Python 3.11 / uv
- PostgreSQL + pgvector
- pytest + ruff

## 下一步任务
等待新的 phase 或 OpenSpec change

## Phase Loop 规则
- Requirements Analysis: 必须像产品经理一样详细，包含字段定义
- Skills/Learning: 错误/模式 → codify 到 skills/ 可复用
- Code Review 失败 → 进入 Fix Phase，不忽视
- Controller NEVER implements code directly
