# Sprint 1 PRD: 自反思集成 + Skill Seed + 法律测试扩展

> PM: Hermes | Tech: Claude Code | Date: 2026-06-07
> 目标: 让自反思 Skills 真正在 Pipeline 中生效，补全法律分类测试

---

## 需求 1: 自反思 Skills 集成到 DraftAgent

### 背景

自反思 Skills 系统已实现（schema/loader/reflector/generator 四个模块），但只作为独立模块验证，没有接入真正的草稿生成流程。DraftAgent 生成草稿时完全不知道 Skills 的存在。

### 产品决策

在 `DraftAgent.generate_draft()` 中加入可选的自反思循环：
1. 生成草稿前，根据意图+风险标签加载相关 Skill
2. 生成草稿后，用 reflector 检查是否符合最佳实践
3. 如果反思不通过，用 Skill 的 resolution_steps 修正草稿
4. 没有 Skill 时，行为完全不变（向后兼容）

### 实现指引

- 文件: `src/ticketpilot/drafting/draft_agent.py`
- 在 `generate_draft()` 方法中：
  1. 从 `ticketpilot.skills.loader` 导入 `load_skill_library`, `select_relevant_skills`
  2. 从 `ticketpilot.skills.reflector` 导入 `reflect_on_draft`
  3. 生成草稿后，尝试加载相关 Skill
  4. 如果有 Skill，运行 `reflect_on_draft()`
  5. 如果 `passed=False`，根据 `suggestions` 修正草稿（在草稿末尾追加缺失的风险声明）
  6. 修正后不再二次反思（避免循环）

- 文件: `src/ticketpilot/drafting/draft_agent.py` 的 `DraftResult` schema
  - 新增字段: `reflection_passed: bool | None = None`
  - 新增字段: `reflection_issues: list[str] = []`
  - 新增字段: `skill_used: str | None = None`  # 被使用的 Skill ID

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python3 -c "
from ticketpilot.drafting.draft_agent import DraftAgent
from ticketpilot.schema.ticket import Ticket, IntentClass, RiskFlag

# 测试 1: 有 Skill 的投诉工单（法律风险）
ticket = Ticket(
    ticket_id='REFLECT-001',
    text='请联系我们律师，准备起诉你们公司',
    intent=IntentClass.COMPLAINT,
    confidence=0.88,
    risk_flags=[RiskFlag.LEGAL_RISK],
)
agent = DraftAgent()
result = agent.generate_draft(ticket)
print(f'✅ 反思结果: passed={result.reflection_passed}, skill={result.skill_used}')
print(f'✅ 草稿长度: {len(result.text)} 字')

# 测试 2: 无 Skill 的普通工单
ticket2 = Ticket(
    ticket_id='REFLECT-002',
    text='查询物流状态',
    intent=IntentClass.LOGISTICS,
    confidence=0.78,
    risk_flags=[],
)
result2 = agent.generate_draft(ticket2)
print(f'✅ 无Skill: passed={result2.reflection_passed}, skill={result2.skill_used}')
"
```

期望输出:
- 反思结果: passed=False 或 True（取决于草稿是否包含法律声明）， skill=legal_v1 或类似
- 无Skill: passed=None, skill=None（向后兼容）

---

## 需求 2: Skill Seed 库

### 背景

PRD 需求 6 定义了 `data/skills/library.json`，但还没创建。自反思集成后需要有初始数据才能生效。

### 产品决策

为 5 个 Agent 各创建 1 个初始 Skill，覆盖最常见的处理模式。

### 实现指引

- 文件: `data/skills/library.json`
- 包含 5 个 Skill:

```json
{
  "version": "1.0",
  "skills": {
    "refund_v1": {
      "skill_id": "refund_v1",
      "intent": "refund",
      "name": "标准退款处理",
      "description": "处理退款请求的标准流程",
      "keywords": ["退款", "退钱", "退货", "退换"],
      "resolution_steps": ["确认订单号", "检查退款政策", "生成退款方案", "告知退款时间"],
      "risk_flags_to_acknowledge": [],
      "tone": "professional",
      "success_count": 10
    },
    "complaint_v1": {
      "skill_id": "complaint_v1",
      "intent": "complaint",
      "name": "标准投诉处理",
      "description": "处理客户投诉，安抚情绪",
      "keywords": ["投诉", "差评", "态度差", "不满意"],
      "resolution_steps": ["表达歉意", "了解问题详情", "提出解决方案", "跟进处理"],
      "risk_flags_to_acknowledge": ["compensation_risk"],
      "tone": "empathetic",
      "success_count": 8
    },
    "legal_v1": {
      "skill_id": "legal_v1",
      "intent": "complaint",
      "name": "法律威胁处理",
      "description": "处理法律威胁类投诉，必须声明法律免责",
      "keywords": ["律师", "起诉", "法院", "法律", "仲裁"],
      "resolution_steps": ["声明法律免责", "记录工单", "转交法务部门", "48小时内回复"],
      "risk_flags_to_acknowledge": ["legal_risk"],
      "tone": "professional",
      "success_count": 5
    },
    "logistics_v1": {
      "skill_id": "logistics_v1",
      "intent": "logistics",
      "name": "物流问题处理",
      "description": "处理物流延迟、丢件等问题",
      "keywords": ["物流", "快递", "发货", "没收到", "丢件"],
      "resolution_steps": ["确认订单号", "查询物流状态", "联系物流方", "给出预计时间"],
      "risk_flags_to_acknowledge": [],
      "tone": "professional",
      "success_count": 7
    },
    "technical_v1": {
      "skill_id": "technical_v1",
      "intent": "technical",
      "name": "技术问题处理",
      "description": "处理APP/网站技术问题",
      "keywords": ["打不开", "闪退", "报错", "无法登录", "bug"],
      "resolution_steps": ["确认设备型号", "确认APP版本", "提供排查步骤", "升级到技术团队"],
      "risk_flags_to_acknowledge": ["account_security_risk"],
      "tone": "professional",
      "success_count": 6
    }
  }
}
```

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python3 -c "
from ticketpilot.skills.loader import load_skill_library

lib = load_skill_library()
print(f'✅ Skills 数量: {len(lib.skills)}')
for sid, skill in lib.skills.items():
    print(f'  - {sid}: {skill.name} (intent={skill.intent}, tone={skill.tone})')
"
```

期望输出:
- Skills 数量: 5
- 列出 5 个 Skill 的 ID、名称、意图、语气

---

## 需求 3: 法律分类扩展测试

### 背景

当前法律分类只有 3 个测试用例（律师、起诉、律师函），需要覆盖更多边界情况。

### 产品决策

增加 8 个测试用例，覆盖：
- 法律威胁变体（仲裁、法院传票、12315 + 法律）
- 边界 case（"律师费" 应该分类为投诉而非其他）
- 非法律 case 不应误判（"法律知识" 不是威胁）

### 实现指引

- 文件: `tests/unit/test_classifier.py`
- 新增测试类 `TestLegalClassification`:

```python
class TestLegalClassification:
    """法律威胁意图分类扩展测试"""

    @pytest.mark.parametrize("text,expected_intent", [
        # 应该分类为 COMPLAINT 的法律威胁
        ("我要向消费者协会投诉并申请仲裁", "complaint"),
        ("已收到法院传票", "complaint"),
        ("12315投诉，准备起诉", "complaint"),
        ("律师函已寄出，请查收", "complaint"),
        ("我要申请劳动仲裁", "complaint"),
        ("请你们法务部门联系我", "complaint"),
        # 边界: 包含法律词但不是威胁
        ("请问你们的退款政策合法吗", "refund"),  # 退款意图优先
        # 非法律 case
        ("查询物流状态", "logistics"),
    ])
    def test_legal_and_non_legal_classification(self, text, expected_intent):
        classifier = IntentClassifier()
        result = classifier.classify(text)
        assert result.intent.value == expected_intent, \
            f"Expected {expected_intent}, got {result.intent.value} for: {text}"
```

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python -m pytest tests/unit/test_classifier.py::TestLegalClassification -v --tb=short 2>&1 | tail -15
```

期望: 所有测试 PASSED，0 FAILED

---

## 需求 4: Skill 持久化（save 功能）

### 背景

`generate_skill_from_success()` 能生成 Skill，但没有保存到文件的功能。自反思循环需要能把新 Skill 写回 `data/skills/library.json`。

### 实现指引

- 文件: `src/ticketpilot/skills/loader.py`
- 新增函数:

```python
def save_skill_library(library: SkillLibrary, path: str = "data/skills/library.json") -> None:
    """保存 Skill 库到 JSON 文件"""
    from pathlib import Path
    import json
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = library.model_dump(mode='json')
    # datetime 序列化
    for skill in data.get('skills', {}).values():
        if skill.get('last_used'):
            skill['last_used'] = skill['last_used'].isoformat()
        if skill.get('created_at'):
            skill['created_at'] = skill['created_at'].isoformat()
    data['updated_at'] = data['updated_at'].isoformat()
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
```

### 验收钩子 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate
python3 -c "
from ticketpilot.skills.loader import load_skill_library, save_skill_library
from ticketpilot.skills.schema import SkillPattern
from datetime import datetime, timezone

# 加载
lib = load_skill_library()
original_count = len(lib.skills)

# 添加新 Skill
lib.skills['test_save'] = SkillPattern(
    skill_id='test_save', intent='test', name='保存测试',
    description='测试保存功能', success_count=1,
)

# 保存
save_skill_library(lib)
print(f'✅ 保存成功: {original_count} → {len(lib.skills)} skills')

# 重新加载验证
lib2 = load_skill_library()
assert 'test_save' in lib2.skills
print(f'✅ 重新加载: test_save 存在={\"test_save\" in lib2.skills}')

# 清理: 删除测试 Skill
del lib.skills['test_save']
save_skill_library(lib)
print(f'✅ 清理完成: {len(lib.skills)} skills')
"
```

期望: 3 行 ✅

---

## 全局验收 ✅

```bash
cd /home/hermes/ticketpilot && source .venv/bin/activate

# 1. 新模块测试
python -m pytest tests/unit/test_skills.py -v --tb=short 2>&1 | tail -5

# 2. 法律分类测试
python -m pytest tests/unit/test_classifier.py::TestLegalClassification -v --tb=short 2>&1 | tail -5

# 3. 全量测试
python -m pytest --tb=no -q 2>&1 | tail -3

# 4. Pipeline 集成验证
python3 -c "
from ticketpilot.skills.loader import load_skill_library
lib = load_skill_library()
print(f'Skills: {len(lib.skills)}')
# 确认 5 个基础 + 可能的新 Skill
assert len(lib.skills) >= 5
print('✅ Skill 库就绪')
"
```

期望:
- 新测试全部 PASSED
- 全量测试 1644+ passed, 0 failed
- Skill 库 ≥ 5 个

最后 commit:
```bash
git add -A && git commit -m "feat: integrate self-reflection into DraftAgent + skill seed + legal test expansion"
```

---

## 约束

1. 不改变现有路由逻辑
2. 不改变现有测试行为（1644 个测试继续通过）
3. 自反思是可选的——没有 Skill 时 DraftAgent 行为完全不变
4. Skill 库是 JSON 文件，不需要数据库迁移
