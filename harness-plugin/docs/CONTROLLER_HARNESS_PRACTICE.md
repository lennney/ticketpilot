# Controller Harness 践行方案

*适用场景：你（主控）直接在 Claude Code 主窗口运行，Claude Code 作为 Controller Agent*
*基于 TicketPilot 项目实践，已验证可行。*

---

## 一、核心理念

```
你（主控）→ Claude Code（Controller）→ Subagent + Skills
                         ↑
                   共享上下文文件
                         ↑
                   error 问题流
                         ↑
                   OpenSpec（状态锚点）
```

**关键原则**：
- OpenSpec 是唯一状态锚点，不创建平行文档
- error 管理是 OpenSpec 的输入层
- 主控窗口压缩时，靠文件记录恢复上下文
- 所有 agent 共享同一个文件体系

---

## 二、文件体系

### 状态锚点（OpenSpec）

```
openspec/
├── changes/{active-change}/   ← 当前 active 变更
│   ├── tasks.md               ← 任务状态追踪（唯一任务源）
│   ├── design.md              ← 架构决策记录
│   └── repair_entry.md       ← 本变更相关问题
├── changes/archive/           ← 已归档变更
└── specs/                     ← 已晋升的 spec
```

### 问题记录（error_memory.jsonl）

```
reports/harness/error_memory.jsonl     ← 实时追加，触发处理阈值后归并
```

### Controller 上下文（已有则复用）

```
docs/harness/
├── chatgpt_controller_context.md   ← 长期状态（Phase、约束、背景）
├── controller_next_actions.md      ← 当前任务 + 已完成记录
├── controller_session_log.md       ← session 间 handoff
├── preflight_checklist.md          ← 每次 session 前检查项
└── agent_learning_rules.md          ← 稳定跨 Phase 规则

subagent_results/                    ← subagent 输出暂存（临时）
```

---

## 三、主控行为规范

### 每次 session 开始

```
1. 读取 openspec/changes/{active}/tasks.md
   → 确认当前任务状态

2. 读取 docs/harness/controller_next_actions.md
   → 了解 next batch

3. 读取 error_memory.jsonl（如有）
   → 检查是否有未处理 P1 error

4. 如需要：读取 docs/harness/agent_learning_rules.md
   → 复习稳定规则
```

### 派发任务

```
1. 更新 tasks.md：待开始 → 进行中
2. 派发 subagent（backend-engineer / code-reviewer）
3. subagent 结果写入 subagent_results/{task_id}_result.md
```

### 验收任务

```
1. 读取 subagent_results/{task_id}_result.md
2. 派发 code-reviewer 审核
3. 审核通过：
   - tasks.md：进行中 → 已完成
   - controller_next_actions.md：写入完成记录
```

### 问题处理

```
1. 发现问题 → 追加到 error_memory.jsonl
   {ts, task, severity, type, symptom, root_cause, fix_applied, resolved}

2. 达到触发条件（5 条未处理 / 手动 / quality gate 失败）
   → /error-to-openspec skill

3. skill 分析：
   - 写入 openspec/changes/{active}/repair_entry.md
   - 需要新变更 → 建议新建 openspec change
```

---

## 四、subagent 派发策略

| 任务类型 | 派发给 | 审核 |
|---------|--------|------|
| 实现功能 | `backend-engineer` | `code-reviewer` |
| 计划/设计 | `project-director` | 主控自己 |
| 代码审核 | `code-reviewer` | - |
| 问题探索 | `Explore` / `general-purpose` | - |
| 验收标准 | `qa-evaluator` | `phase-supervisor` |

**派发原则**：
- 保持 subagent prompt 自包含（它不读之前的对话）
- 明确输出路径：`subagent_results/{task_id}_result.md`
- 明确验收标准（来自 tasks.md）

---

## 五、技术债整理流程

### 阶段 1：清点

```
1. /error-to-openspec
   → 输出：未处理 error 按 type 分组

2. 我直接读代码库找问题：
   - 重复代码
   - 命名不一致
   - 注释缺失
```

### 阶段 2：分类

| 级别 | 定义 | 处理 |
|------|------|------|
| A. 架构级 | 影响模块边界、数据契约 | 新 OpenSpec change |
| B. 代码级 | 坏味道、重复、命名 | 重构 + unit test |
| C. 文档级 | 注释缺失、边界模糊 | 直接修复 |
| D. 已知/可忽略 | 不影响功能，低优先级 | 记录但不动 |

### 阶段 3：创建技术债专项（可选）

如 A 类问题较多，创建：

```
openspec/changes/address-technical-debt/
├── proposal.md    ← 问题清单 + 分级
├── design.md      ← 优先级排序
├── tasks.md      ← A/B/C/D 分类任务
└── repair_entry.md
```

### 阶段 4：逐个处理

```
tasks.md：
## A 类（架构级）
- [ ] A-1: claim_guard.py GuardResult 扩展问题
- [ ] A-2: ...

## B 类（代码级）
- [ ] B-1: 统一命名规范
```

---

## 六、避免文档膨胀的原则

1. **只记非显而易见的事**（代码里有的不重复）
2. **frontmatter 放机器元数据，主体用 markdown**
3. **每文件 < 100 行**（超了归档旧内容）
4. **CONTEXT.md 有 TTL**（每 7 天检查，过期移走）
5. **subagent_results/ 是临时的**（任务完成后可删）

---

## 七、error-to-openspec Skill（核心）

```markdown
# Skill: error-to-openspec

## 触发时机
- error_memory.jsonl 累计 5 条未处理
- quality gate 失败后
- 手动 /error-to-openspec

## 流程
1. 读取 error_memory.jsonl（severity=P1 或 unresolved=true）
2. 按当前 active OpenSpec change 分组
3. 对每条 error：
   - 写入 change 的 repair_entry.md（标记 ⚠️ UNRESOLVED）
   - 需要新 change → 写入 chatgpt_controller_context.md suggestions
4. 标记已处理的 error 条目
5. 输出处理摘要

## 输出示例
处理了 3 条新 error：
- #12: dimension mismatch → 写入 repair_entry.md
- #13: guard type confusion → repair_entry.md ⚠️ UNRESOLVED
- #14: → 建议新建 openspec change
```

---

## 八、TicketPilot 当前状态（2026-05-07）

### 当前 Phase
**Phase 15.3 刚完成** — Pipeline-to-Chat Adapter

### Active OpenSpec Change
`align-chat-support-product-experience`

### tasks.md 当前状态
```
Phase 15.1: ✅ 已完成（规划）
Phase 15.2: ✅ 已完成（Chat Demo UI Skeleton）
Phase 15.3: ✅ 已完成（Pipeline-to-Chat Adapter）
Phase 15.4-15.8: 待开始
```

### Phase 14 暂停状态
Phase 14 guard taxonomy 14.2/14.2.1 已完成，14.3-14.7 暂停，guard 作为安全基础保留。

### 技术债待整理
- Phase 14 guard taxonomy 剩余任务（14.3-14.7）
- Phase 15 chat demo 后续任务（15.4-15.8）
- 需评估现有 error_memory.jsonl 中的 P1 条目

---

## 九、下一步建议

**选项 A**：继续 Phase 15.4（Streamlit 聊天界面集成）
→ 派发 subagent 实现 chat UI 和 pipeline 的连接

**选项 B**：技术债整理
→ 运行 /error-to-openspec，读取 error_memory.jsonl，分类技术债

**选项 C**：先完善 controller harness 文件
→ 在 TicketPilot 中建立这套践行的模板（已有 harness 文档，需要确认覆盖度）

你选哪个？
