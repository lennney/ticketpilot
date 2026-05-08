# TicketPilot Interview Talking Points

> Chat support copilot talking points for interviews.
>
> This is a local portfolio demo, not a production system.

---

## 1-Minute Version

> "TicketPilot 是我做的一个面向电商售后的 Chat-style AI Copilot 原型（Phase 15 完成）。用户通过聊天界面提交工单，系统在多轮对话上下文中完成分类、风险判断、知识检索、证据化草稿生成和人工审核。比传统工单列表更直观——保持会话历史、证据面板侧边栏展示、高风险升级通知突出。
>
> 项目经历 9 个阶段迭代：从建 101 条数据基底，到换真实嵌入发现瓶颈在知识覆盖，到定向补知识发现配置静默回退 bug，到精细化评测发现 78% 的错误是粒度问题，到 LLM 草稿生成，到 Guard-Aware Prompting（84% pass rate），到最近的 Chat UI 对齐。每个阶段回答一个具体的产品问题。"

---

## 3-Minute Version

> "TicketPilot 的出发点是展示 AI 产品的边界该怎么设计，以及怎么通过迭代验证做判断。
>
> 产品现在是一个 Chat-style AI Copilot——用户通过聊天界面提交工单，系统在多轮上下文中完成分类、风险判断、知识检索、草稿生成和人工审核。比传统工单列表更直观：保持会话历史、证据面板侧边栏展示、高风险升级通知突出。Pipeline-to-Chat Adapter 把管道输出转换成聊天消息格式。
>
> 项目分 9 个阶段。Phase 7 打数据基底——101 条工单，评测流水线。Phase 8 换真实嵌入——Top-1 从 31.7% 到 42.6%，但错例分析发现 fake 和 real 的 41 个错例完全一致，说明瓶颈在知识覆盖不在 embedding。Phase 9 补知识——加 11 条 P0 记录，同时发现 load_dotenv() 没被调用，评测静默回退到 fake。建了 Provider Identity Gate 修复这个 bug。
>
> Phase 10 建 doc-ID 级别细粒度标注，Doc-ID Recall@10 达 91.9%。78% 的"错误"是评测粒度问题。Phase 11-13 做 LLM 草稿生成和 Guard-Aware Prompting——deepseek-v4-pro 达到 84% guard pass rate。
>
> Phase 15 把产品包装成 Chat-style AI Copilot。把产品从'后台工单流水线'变成'前台对话产品'。这个叙事转换让产品更容易被理解——用户知道这是'AI 助手'，而不是'安全护栏系统'。"

---

## Chat-Specific Talking Points

### Why design as chat interface instead of ticket list?

> "工单列表界面的问题是上下文丢失——客服需要反复问用户已经说过的信息。比如用户问'我之前那个订单退款了吗'，工单列表没法理解'之前那个'指的是哪条。聊天界面天然保持会话历史，用户说'接着刚才那个问题'系统能理解。
>
> 聊天更符合用户直觉。普通用户每天用微信、Slack 这种聊天工具，不需要学习成本。而且证据面板和风险通知可以通过侧边栏和消息组件展示，不打断对话流程。"

### How is multi-turn context maintained?

> "Chat UI 在后端维护会话状态。每条消息关联到同一个 session_id。当用户发送新消息时，系统会携带之前的消息历史一起发送给分类器和风险评估模块。
>
> Pipeline 输出通过 Pipeline-to-Chat Adapter 转换成 Chat 消息格式。Adapter 负责从 pipeline 输出中提取意图、风险、证据引用等信息，渲染成用户可见的聊天消息。证据面板基于引用 chunk_id 动态加载来源详情。"

### How is human review triggered in chat?

> "高风险场景自动触发人工审核。当 pipeline 输出包含 HIGH severity 标记、Unsupported claims 或 Citation validation failure 时，审核操作按钮会在聊天中显示。
>
> 审核员可以选择批准、编辑、升级或拒绝。审核决策实时写入 ReviewDecision JSONL 文件，保留完整的审计追踪。这个流程完全内嵌在聊天 UI 中，不需要跳转到单独的审核界面。"

### Why shift from "guard architecture" to "chat-style AI copilot"?

> "'Guard architecture' 是技术团队的视角——我们关心的是安全护栏、ClaimGuard、引用校验这些。但对用户来说，这些是不可见的、后台的技术约束。
>
> Phase 15 的核心改动是叙事转换——把技术语言翻译成用户语言。用户理解'AI 助手'，不理解'安全护栏系统'。Chat UI 让安全功能变得可见：风险升级通知告诉用户'这条消息有风险'，人工审核按钮告诉用户'这条需要人工确认'。"

### What are the limitations of the Chat UI MVP?

> "Chat UI 是 MVP 级别，不是生产级产品。主要限制：
>
> - 多轮意图追踪还不完善——复杂的多轮对话场景可能丢失上下文
> - 证据面板加载依赖 chunk_id 引用——如果引用损坏，面板显示会受影响
> - 没有登录和多用户支持——当前是单用户会话
> - UI/UX 还需要迭代打磨
>
> 下一步可以继续优化 Chat UX，比如主动建议草稿修改、审核效率提升等。"

---

## Q&A for Chat UX Design Rationale

**Q: Why not use a traditional ticket list interface?**
> Traditional ticket lists don't maintain conversation history. Users have to re-explain context across multiple tickets. Chat UI naturally preserves context and is more intuitive for users.

**Q: How does the evidence panel work?**
> When the AI generates a draft with citations like `[chunk_id]`, clicking on the citation loads the source document in the sidebar panel. Panel shows document type, content, and relevance score.

**Q: What happens when risk escalation is triggered?**
> A prominent banner appears in the chat warning about high risk. Human review buttons (Approve/Edit/Escalate/Reject) appear in the message. Review decision is recorded to JSONL audit trail.

**Q: Can users switch between Chat UI and Pipeline API?**
> Yes. Chat UI is one entry point; Pipeline API is another. Both use the same backend pipeline for intent classification, risk assessment, retrieval, and draft generation.

---

## Next Steps Discussion

**Q: What's the next optimization direction?**
> "Phase 15 已完成 Chat UI MVP。下一步可以继续优化 Chat UX：
>
> 1. 多轮意图追踪——让系统能理解'接着说'、'刚才那个订单'这类指代
> 2. 主动建议——基于上下文主动建议下一步操作，比如'要不要查一下物流信息'
> 3. 审核效率提升——批量审核、快捷键支持、模板化回复
> 4. 回到 Phase 10 诊断——7 个 zero-hit 案例做 query expansion，32 个 partial-hit 案例做 fusion ranking 优化"

**Q: How would you improve the chat UX?**
> "几个方向：
>
> - 主动建议草稿修改——基于 ClaimGuard 状态建议优化方向
> - 上下文敏感的帮助——用户犹豫时提供引导
> - 审核效率工具——快捷键、批量操作、模板化回复
> - 响应式设计——支持移动端访问"

---

## Boundary Wording Reminders

When discussing the chat UI, remember:

- **NOT production-ready**: Chat UI is MVP-level, UX iterative
- **NOT real enterprise data**: Seed data only, synthetic tickets and knowledge records
- **NOT auto-send**: Human review is mandatory for high-risk tickets
- **Pipeline verification only**: Retrieval metrics measure pipeline connectivity, not semantic quality
- **No LLM by default**: FakeLLMProvider used for offline verification

---

## File Reference

| File | Description |
|------|-------------|
| `src/ticketpilot/chat/app.py` | Chat UI main entry |
| `src/ticketpilot/chat/adapter.py` | Pipeline-to-Chat Adapter |
| `src/ticketpilot/chat/schemas.py` | Chat data schemas |
| `src/ticketpilot/chat/pages/` | Streamlit pages (evidence panel, risk escalation) |

---

*Last updated: 2026-05-08*
*Based on Phase 15 Chat Support Alignment*
