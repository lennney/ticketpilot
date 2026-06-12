# TicketPilot 文档维护公约

> 文档和代码一样重要。**未更新文档的阶段 = 未完成的阶段。**

---

## 核心原则

### 1. "No docs change" = 有 bug

任何代码变更如果在 `docs/INDEX.md` 中涉及的文件没有同步更新，说明变更没有经过完整的思考。

**触发条件：**
- 新增模块、修改 API、改动了数据格式 → 必须更新对应文档
- 新增文件 → 更新 `docs/INDEX.md`
- 完成一个阶段 → 更新 `CHANGELOG.md`

### 2. CHANGELOG 是阶段验收的硬门槛

每次阶段完成/合并前，`CHANGELOG.md` 必须：

| 检查项 | 要求 |
|--------|------|
| `[Unreleased]` 有内容 | ✅ |
| Added/Changed/Fixed 分类 | ✅ |
| 关键指标变化（如有） | ✅ |
| 影响到的文档标注 | ✅ |

**未更新 CHANGELOG 的 commit 不能标记为 `[verified]`。**

### 3. 文档优先于代码

写代码前先确认文档在哪里。规则：
1. 先读 `docs/INDEX.md` 确定受影响的文档
2. 如果是新功能，先更新文档框架再写代码
3. 改完后确认文档事实准确

### 4. 旧文档标记

如果修改了某模块但没有时间完整更新它的旧文档：

```
⚠️ 此文档在 YYYY-MM-DD（Scoring Classifier / Phase XX）后未更新。
   修改时优先检查是否需要同步。
```

不需要同时更新所有旧文档，但**至少要在受影响文档顶部加过期标记**。

---

## 更新时机

| 时机 | 必须更新 | 建议更新 |
|------|---------|---------|
| **阶段完成时** (merge) | CHANGELOG.md + 受影响的 technical docs | docs/INDEX.md 的"最后更新"列 |
| **新增文件** | docs/INDEX.md | 无 |
| **重构不改接口** | 无 | 受影响模块的 docstring |
| **评测数据/指标变化** | CHANGELOG.md | 任何引用了旧指标的文档 |
| **淘汰旧功能** | 标记为 deprecated + 更新 INDEX | 无 |

---

## 文档质量检查清单

写/更新一篇文档时检查：

### 事实准确性
- [ ] 代码路径与实际匹配（`src/ticketpilot/...`）
- [ ] 类/方法名与实际代码一致
- [ ] 配置项名称大小写正确
- [ ] 指标数字可复现

### 结构完整性
- [ ] 有标题层级（`#` → `##` → `###`）
- [ ] 代码块标注语言（`python` / `bash`）
- [ ] 表格有对齐和说明
- [ ] 链接可访问

### AI 友好性
- [ ] 文档可以被 AI Agent 独立理解（不需要外部上下文）
- [ ] 关键路径和文件有明确引用
- [ ] 合同/边界条件显式说明

---

## 清理规则

| 类型 | 保留策略 | 示例 |
|------|---------|------|
| **实施计划** (docs/plans/) | 阶段归档后移入 `plans/archive/` 或删除 | `2026-06-11-scoring-classifier.md` |
| **产品设计** (docs/product/) | 永久保留，每个独立重要决策 | `draft-quality-gate.md` |
| **技术文档** (docs/technical/) | 永久保留，修改时更新 | `retrieval_architecture.md` |
| **Checkpoint** (docs/CHECKPOINT_*.md) | 归档到 `CHANGELOG.md` 后删除 | `CHECKPOINT_2026-06-11-PHASE.md` |
| **Harness 文档** (docs/harness/) | 永久保留 | `PHASE_LOOP.md` |
| **作品集** (docs/portfolio/) | 按需更新 | `METRICS.md` |

---

## 自动化建议

### 可以但不强制

```bash
# 检查 CHANGELOG 是否更新
git diff HEAD --name-only | grep -q CHANGELOG.md || echo "⚠️ CHANGELOG 未更新"

# 检查 INDEX 是否同步
git diff HEAD --name-only | grep -v CHANGELOG.md | grep -v docs/INDEX.md | \
  grep -E "\.(py|json|yaml|yml)$" | head -1 && \
  echo "⚠️ 代码有变更，请检查 docs/INDEX.md 是否需要同步"
```

---

> **一句话总结**: 每完成一件事，停下来更新一次文档。不更新等于没做完。
