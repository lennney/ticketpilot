# TicketPilot 自反思 Skills 系统 PRD

> PM: Hermes | Tech: Claude Code | Date: 2026-06-07

---

## 背景

TicketPilot 当前问题：每次处理工单都是从零开始，不会从过去的成功经验中学习。

Klarna 的自反思循环把幻觉率从 5% 降到了 1.2%。我们需要类似机制。

## 产品决策

选"自反思 Skills"不选"静态模板库"，因为：
- 静态模板：所有工单用同一套模板
- 自反思 Skills：Agent 从成功案例中学习，动态选择最佳实践

## 架构设计

```
data/skills/                    ← Skill 存储目录
  refund_v1.json                ← 退款类最佳实践
  complaint_v1.json             ← 投诉类最佳实践
  logistics_v1.json             ← 物流类最佳实践
  ...

src/ticketpilot/skills/         ← Skill 模块
  __init__.py
  schema.py                     ← Skill 数据结构
  loader.py                     ← 加载相关 Skill
  reflector.py                  ← 自反思循环
  generator.py                  ← 从成功案例生成 Skill
```

---

## 需求 1: Skill 数据结构

### 实现

文件: `src/ticketpilot/skills/schema.py`

```python
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class SkillPattern(BaseModel):
    """一个解决模式（Skill）的数据结构"""
    skill_id: str = Field(..., min_length=1)
    intent: str  # 对应的意图分类 (refund, complaint, ...)
    name: str  # 人类可读名称
    description: str  # 模式描述
    keywords: list[str] = Field(default_factory=list)  # 触发关键词
    resolution_steps: list[str] = Field(default_factory=list)  # 解决步骤
    risk_flags_to_acknowledge: list[str] = Field(default_factory=list)  # 必须承认的风险
    tone: str = "professional"  # 语气: professional, empathetic, urgent
    success_count: int = 0  # 成功使用次数
    last_used: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class SkillLibrary(BaseModel):
    """Skill 库"""
    version: str = "1.0"
    skills: dict[str, SkillPattern] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
```

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python3 -c "
from ticketpilot.skills.schema import SkillPattern, SkillLibrary
import json

# 测试 SkillPattern 创建
skill = SkillPattern(
    skill_id='refund_v1',
    intent='refund',
    name='标准退款处理',
    description='处理退款请求的标准流程',
    keywords=['退款', '退钱'],
    resolution_steps=['确认订单号', '检查退款政策', '生成退款方案'],
    risk_flags_to_acknowledge=[],
    tone='professional',
    success_count=5,
)
print(f'✅ SkillPattern: {skill.skill_id}, {skill.name}')

# 测试 SkillLibrary 创建
lib = SkillLibrary(skills={'refund_v1': skill})
print(f'✅ SkillLibrary: {len(lib.skills)} skills')

# 测试序列化
data = lib.model_dump_json()
print(f'✅ Serialization: {len(data)} chars')
"
```

期望输出: 3 行都是 ✅

---

## 需求 2: Skill 加载器

### 实现

文件: `src/ticketpilot/skills/loader.py`

根据意图分类和风险标签，加载最相关的 Skill。

```python
from ticketpilot.skills.schema import SkillPattern, SkillLibrary

def load_skill_library(path: str = "data/skills/library.json") -> SkillLibrary:
    """从 JSON 文件加载 Skill 库"""
    import json
    from pathlib import Path
    p = Path(path)
    if not p.exists():
        return SkillLibrary()
    data = json.loads(p.read_text(encoding="utf-8"))
    return SkillLibrary(**data)

def select_relevant_skills(
    library: SkillLibrary,
    intent: str,
    risk_flags: list[str],
    top_k: int = 3,
) -> list[SkillPattern]:
    """选择最相关的 Skill
    
    优先级:
    1. 意图完全匹配
    2. 风险标签匹配
    3. 成功次数高的优先
    """
    candidates = []
    for skill in library.skills.values():
        score = 0
        if skill.intent == intent:
            score += 10
        for flag in risk_flags:
            if flag in skill.risk_flags_to_acknowledge:
                score += 5
        score += skill.success_count
        if score > 0:
            candidates.append((score, skill))
    
    candidates.sort(key=lambda x: x[0], reverse=True)
    return [skill for _, skill in candidates[:top_k]]
```

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python3 -c "
from ticketpilot.skills.schema import SkillPattern, SkillLibrary
from ticketpilot.skills.loader import select_relevant_skills

# 创建测试库
lib = SkillLibrary(skills={
    'refund_v1': SkillPattern(
        skill_id='refund_v1', intent='refund', name='退款处理',
        description='标准退款', success_count=5,
    ),
    'complaint_v1': SkillPattern(
        skill_id='complaint_v1', intent='complaint', name='投诉处理',
        description='标准投诉', success_count=3,
    ),
    'legal_v1': SkillPattern(
        skill_id='legal_v1', intent='complaint', name='法律威胁处理',
        description='法律风险', risk_flags_to_acknowledge=['legal_risk'], success_count=2,
    ),
})

# 测试: 退款意图
skills = select_relevant_skills(lib, 'refund', [])
print(f'✅ refund: {[s.skill_id for s in skills]}')  # [refund_v1]

# 测试: 投诉意图 + 法律风险
skills = select_relevant_skills(lib, 'complaint', ['legal_risk'])
print(f'✅ complaint+legal: {[s.skill_id for s in skills]}')  # [legal_v1, complaint_v1]

# 测试: 未知意图
skills = select_relevant_skills(lib, 'unknown', [])
print(f'✅ unknown: {[s.skill_id for s in skills]}')  # []
"
```

期望输出:
- refund: [refund_v1]
- complaint+legal: [legal_v1, complaint_v1]
- unknown: []

---

## 需求 3: 自反思循环

### 实现

文件: `src/ticketpilot/skills/reflector.py`

Agent 生成草稿后，自反思检查是否符合 Skill 中的最佳实践。

```python
from ticketpilot.skills.schema import SkillPattern

class ReflectionResult:
    """自反思结果"""
    def __init__(self, passed: bool, issues: list[str], suggestions: list[str]):
        self.passed = passed
        self.issues = issues
        self.suggestions = suggestions

def reflect_on_draft(
    draft_text: str,
    skill: SkillPattern,
    risk_flags: list[str],
) -> ReflectionResult:
    """检查草稿是否符合 Skill 最佳实践
    
    检查项:
    1. 是否承认了必要的风险标签
    2. 是否包含了解决步骤中的关键元素
    3. 语气是否匹配
    """
    issues = []
    suggestions = []
    
    # 检查风险标签
    for flag in skill.risk_flags_to_acknowledge:
        if flag == 'legal_risk' and '律师' not in draft_text and '法律' not in draft_text:
            issues.append(f'缺少法律风险声明: {flag}')
            suggestions.append('添加法律风险相关的免责声明')
    
    # 检查解决步骤
    for step in skill.resolution_steps:
        if '订单号' in step and '订单' not in draft_text:
            issues.append(f'缺少关键步骤: {step}')
            suggestions.append(f'添加: {step}')
    
    # 检查语气
    if skill.tone == 'empathetic' and '抱歉' not in draft_text and '理解' not in draft_text:
        suggestions.append('建议添加同理心表达')
    
    passed = len(issues) == 0
    return ReflectionResult(passed=passed, issues=issues, suggestions=suggestions)
```

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python3 -c "
from ticketpilot.skills.schema import SkillPattern
from ticketpilot.skills.reflector import reflect_on_draft

# 创建法律风险 Skill
skill = SkillPattern(
    skill_id='legal_v1',
    intent='complaint',
    name='法律威胁处理',
    description='处理法律威胁',
    resolution_steps=['确认订单号', '转交法务'],
    risk_flags_to_acknowledge=['legal_risk'],
    tone='professional',
)

# 测试 1: 草稿缺少法律声明
result = reflect_on_draft(
    '您好，我们会尽快处理您的问题。',
    skill,
    ['legal_risk'],
)
print(f'✅ 缺少声明: passed={result.passed}, issues={len(result.issues)}')

# 测试 2: 草稿包含法律声明
result = reflect_on_draft(
    '您好，我们已收到您的法律咨询。根据我们的退款政策，我们会尽快处理。',
    skill,
    ['legal_risk'],
)
print(f'✅ 包含声明: passed={result.passed}, issues={len(result.issues)}')
"
```

期望输出:
- 缺少声明: passed=False, issues=1
- 包含声明: passed=True, issues=0

---

## 需求 4: Skill 生成器

### 实现

文件: `src/ticketpilot/skills/generator.py`

从成功的人工审核案例中自动提取 Skill。

```python
from datetime import datetime, timezone
from ticketpilot.skills.schema import SkillPattern

def generate_skill_from_success(
    intent: str,
    original_text: str,
    approved_draft: str,
    risk_flags: list[str],
    feedback: str = "",
) -> SkillPattern:
    """从成功案例生成 Skill
    
    提取:
    1. 关键词 (从原文提取)
    2. 解决步骤 (从草稿提取)
    3. 风险标签
    """
    import uuid
    
    # 提取关键词 (简单实现: 取原文中的高频词)
    keywords = []
    for word in ['退款', '投诉', '物流', '发货', '赔偿', '律师', '起诉']:
        if word in original_text:
            keywords.append(word)
    
    # 提取解决步骤 (简单实现: 按句号分割)
    steps = [s.strip() for s in approved_draft.split('。') if len(s.strip()) > 5][:5]
    
    # 生成 Skill
    skill_id = f'{intent}_{uuid.uuid4().hex[:8]}'
    return SkillPattern(
        skill_id=skill_id,
        intent=intent,
        name=f'{intent}处理模式',
        description=f'从成功案例自动生成: {original_text[:50]}...',
        keywords=keywords,
        resolution_steps=steps,
        risk_flags_to_acknowledge=risk_flags,
        success_count=1,
        last_used=datetime.now(timezone.utc),
    )
```

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python3 -c "
from ticketpilot.skills.generator import generate_skill_from_success

# 测试: 从成功案例生成 Skill
skill = generate_skill_from_success(
    intent='refund',
    original_text='我要退款，订单号123456，收到的商品有质量问题',
    approved_draft='您好，已收到您的退款申请。我们会尽快处理。',
    risk_flags=[],
    feedback='处理得当',
)
print(f'✅ skill_id: {skill.skill_id}')
print(f'✅ keywords: {skill.keywords}')
print(f'✅ steps: {len(skill.resolution_steps)} steps')
print(f'✅ success_count: {skill.success_count}')
"
```

期望输出:
- skill_id: refund_xxxxxxxx
- keywords: ['退款']
- steps: 1 steps
- success_count: 1

---

## 需求 5: 集成到 Pipeline

### 实现

修改 `src/ticketpilot/drafting/draft_agent.py`，在生成草稿后加入自反思循环。

```python
# 在 DraftAgent.generate_draft() 中:
# 1. 加载相关 Skill
# 2. 生成草稿
# 3. 自反思检查
# 4. 如果不通过，修正后重新生成
```

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python3 -c "
from ticketpilot.skills.schema import SkillPattern, SkillLibrary
from ticketpilot.skills.loader import select_relevant_skills
from ticketpilot.skills.reflector import reflect_on_draft
from ticketpilot.skills.generator import generate_skill_from_success

# 完整流程测试
lib = SkillLibrary(skills={
    'refund_v1': SkillPattern(
        skill_id='refund_v1', intent='refund', name='退款处理',
        description='标准退款', resolution_steps=['确认订单号'],
        success_count=5,
    ),
})

# 1. 加载相关 Skill
skills = select_relevant_skills(lib, 'refund', [])
print(f'✅ 加载: {len(skills)} skills')

# 2. 生成草稿 (模拟)
draft = '您好，已收到您的退款申请。'

# 3. 自反思
result = reflect_on_draft(draft, skills[0], [])
print(f'✅ 反思: passed={result.passed}')

# 4. 生成新 Skill
new_skill = generate_skill_from_success(
    'refund', '退款', draft, [],
)
print(f'✅ 新Skill: {new_skill.skill_id}')
"
```

期望输出:
- 加载: 1 skills
- 反思: passed=True (无风险标签)
- 新Skill: refund_xxxxxxxx

---

## 需求 6: 初始 Skill 库

### 实现

创建 `data/skills/library.json`，包含 5 个初始 Skill（对应 5 个 Agent）。

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python3 -c "
from ticketpilot.skills.loader import load_skill_library
lib = load_skill_library()
print(f'✅ Skills: {len(lib.skills)}')
for skill_id, skill in lib.skills.items():
    print(f'  - {skill_id}: {skill.name} ({skill.intent})')
"
```

期望输出:
- Skills: 5+
- 列出每个 Skill 的 ID、名称、意图

---

## 全局验收 ✅

所有需求完成后:

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate

# 1. 运行新模块测试
python -m pytest tests/unit/test_skills.py -v --tb=short 2>&1 | tail -10

# 2. 运行全量测试
python -m pytest --tb=no -q 2>&1 | tail -3

# 3. 运行 demo
python scripts/generate_product_evidence.py 2>&1 | grep -E "SUMMARY|Skills" -A 5
```

期望:
- 新测试全部 PASSED
- 全量测试 0 failed
- Demo 输出包含 Skill 信息

最后 commit:
```bash
git add -A && git commit -m "feat: self-reflection skills system — loader, reflector, generator"
```

---

## 约束

1. **不改变现有路由逻辑** — Orchestrator 不变
2. **不改变现有测试** — 1644 个测试必须继续通过
3. **Skill 是可选的** — 没有 Skill 时，Agent 行为不变
4. **自反思是可选的** — 反思失败时，使用原始草稿
5. **Skill 库是 JSON 文件** — 不需要数据库

---

## PM 叙事 (简历/面试用)

> "我发现客服系统每次处理工单都是从零开始，不会从过去的成功经验中学习。我设计了一个自反思 Skills 系统，Agent 会自动加载相关场景的最佳实践，生成草稿后自我审查是否符合这些实践。如果不符，会自动修正。同时，成功的人工审核案例会自动提取为新的 Skill，形成正向循环。这把首次解决率从 X% 提升到 Y%。"
