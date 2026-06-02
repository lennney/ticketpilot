# TicketPilot 数据集扩充方案

**方案日期：** 2026-05-29  
**目标：** 扩充知识库和评测数据集，提升系统覆盖范围和评测可信度  

---

## 一、现有数据集分析

### 1.1 知识库现状

| 类型 | 数量 | 说明 |
|------|------|------|
| FAQ | 41条 | 常见问题解答 |
| Policy | 34条 | 政策文档 |
| Case | 31条 | 案例文档 |
| **总计** | **106条** | 知识库文档 |

### 1.2 评测数据现状

| 场景 | 数量 | 占比 |
|------|------|------|
| refund（退款） | 14条 | 13.9% |
| account_issue（账号问题） | 13条 | 12.9% |
| complaint（投诉） | 13条 | 12.9% |
| logistics（物流） | 11条 | 10.9% |
| return_exchange（退换货） | 11条 | 10.9% |
| technical_issue（技术问题） | 9条 | 8.9% |
| product_consulting（产品咨询） | 8条 | 7.9% |
| other（其他） | 8条 | 7.9% |
| invoice（发票） | 5条 | 5.0% |
| billing（账单） | 4条 | 4.0% |
| account+privacy（账号+隐私） | 2条 | 2.0% |
| refund+complaint（退款+投诉） | 3条 | 3.0% |
| **总计** | **101条** | 100% |

### 1.3 风险标志覆盖

| 风险标志 | 数量 | 占比 |
|----------|------|------|
| complaint_risk（投诉风险） | 32条 | 31.7% |
| policy_conflict（政策冲突） | 16条 | 15.8% |
| compensation_risk（补偿风险） | 15条 | 14.9% |
| insufficient_evidence（证据不足） | 12条 | 11.9% |
| account_security_risk（账号安全） | 7条 | 6.9% |
| privacy_risk（隐私风险） | 7条 | 6.9% |
| legal_risk（法律风险） | 8条 | 7.9% |
| low_confidence（低置信度） | 3条 | 3.0% |

---

## 二、问题分析

### 2.1 数据量不足

| 维度 | 现状 | 目标 | 差距 |
|------|------|------|------|
| 知识库文档 | 106条 | 300+条 | 194条 |
| 评测工单 | 101条 | 300+条 | 199条 |
| 场景覆盖 | 12种 | 20+种 | 8种 |
| 风险覆盖 | 8种 | 10+种 | 2种 |

### 2.2 场景覆盖不全

**缺失的场景：**
- 🚫 **多轮对话** - 当前都是单轮问答
- 🚫 **边界case** - 模糊意图、多重风险
- 🚫 **复杂场景** - 多个问题混合
- 🚫 **方言/口语化** - 非正式表达
- 🚫 **情绪化表达** - 愤怒、焦虑、失望

### 2.3 边界case不足

**需要补充的边界case：**
- 意图模糊：用户问题涉及多个意图
- 风险叠加：多个风险同时出现
- 证据缺失：知识库中没有相关信息
- 政策冲突：不同政策之间存在矛盾
- 极端情况：用户威胁、法律纠纷

---

## 三、数据集扩充方案

### 3.1 知识库扩充（目标：300+条）

#### 方案A：DeepEval Synthesizer 自动生成（推荐）

**原理：** 使用DeepEval的Synthesizer从现有知识库自动生成新文档

**实现代码：**
```python
from deepeval.synthesizer import Synthesizer

synthesizer = Synthesizer()

# 从现有知识库生成新文档
new_docs = synthesizer.generate_goldens_from_docs(
    document_paths=[
        "data/knowledge/faq_seed.json",
        "data/knowledge/policy_seed.json",
        "data/knowledge/case_seed.json"
    ],
    max_goldens_per_document=3,  # 每个文档生成3个新文档
    num_evolutions=2  # 进化2次，增加多样性
)

# 保存新文档
synthesizer.save_goldens(new_docs, "data/knowledge/generated_docs.json")
```

**预期效果：**
- 106个文档 × 3个新文档 = 318个新文档
- 总计：106 + 318 = 424个文档

#### 方案B：LLM生成 + 人工审核

**原理：** 使用DeepSeek生成新文档，人工审核

**实现代码：**
```python
import openai

def generate_knowledge_docs(doc_type: str, count: int) -> list[dict]:
    """使用LLM生成知识库文档."""
    
    prompt = f"""
    你是客服知识库专家。请生成{count}个{doc_type}类型的客服知识库文档。
    
    每个文档包含：
    1. title: 文档标题
    2. content: 文档内容
    3. category: 分类
    4. tags: 标签列表
    
    请以JSON格式输出。
    """
    
    response = openai.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": prompt}]
    )
    
    return json.loads(response.choices[0].message.content)
```

**预期效果：**
- FAQ: 41 → 100条（+59条）
- Policy: 34 → 80条（+46条）
- Case: 31 → 80条（+49条）
- 总计：106 → 260条（+154条）

#### 方案C：公开数据集适配

**可用的公开数据集：**

| 数据集 | 来源 | 规模 | 适配难度 |
|--------|------|------|---------|
| customer_support_conversations | HuggingFace | 10k+ | 中等 |
| smoltalk-chinese | OpenCSG | 50k+ | 低 |
| Customer Service QA | Kaggle | 5k+ | 中等 |

**适配步骤：**
1. 下载公开数据集
2. 转换为TicketPilot格式
3. 人工审核和筛选
4. 导入知识库

---

### 3.2 评测数据扩充（目标：300+条）

#### 方案A：DeepEval Synthesizer 自动生成（推荐）

**实现代码：**
```python
from deepeval.synthesizer import Synthesizer

synthesizer = Synthesizer()

# 从知识库生成评测数据
goldens = synthesizer.generate_goldens_from_docs(
    document_paths=[
        "data/knowledge/faq_seed.json",
        "data/knowledge/policy_seed.json",
        "data/knowledge/case_seed.json"
    ],
    max_goldens_per_document=5,  # 每个文档生成5个测试用例
    num_evolutions=2  # 进化2次，增加多样性
)

# 保存评测数据
synthesizer.save_goldens(goldens, "data/eval/eval_dataset.json")
```

**预期效果：**
- 106个文档 × 5个测试用例 = 530个测试用例
- 总计：101 + 530 = 631个测试用例

#### 方案B：边界case专项生成

**原理：** 专门生成边界case和复杂场景

**实现代码：**
```python
def generate_edge_cases() -> list[dict]:
    """生成边界case."""
    
    edge_cases = [
        # 意图模糊
        {
            "input": "我买的手机有问题，想退货，但是已经过了7天，而且我之前已经换过一次了",
            "expected_intent": "refund",  # 模糊：退款还是换货？
            "expected_risk_flags": ["policy_conflict", "complaint_risk"],
            "ground_truth": "我理解您的情况。根据政策..."
        },
        # 风险叠加
        {
            "input": "你们的产品有安全隐患，我已经受伤了，我要投诉并要求赔偿",
            "expected_intent": "complaint",
            "expected_risk_flags": ["legal_risk", "compensation_risk", "complaint_risk"],
            "ground_truth": "非常抱歉听到您受伤的消息..."
        },
        # 证据缺失
        {
            "input": "我之前在你们这里买过东西，但是找不到订单了，能帮我查一下吗？",
            "expected_intent": "account_issue",
            "expected_risk_flags": ["insufficient_evidence"],
            "ground_truth": "我理解您找不到订单的困扰..."
        }
    ]
    
    return edge_cases
```

**预期效果：**
- 生成50+个边界case
- 覆盖意图模糊、风险叠加、证据缺失等场景

#### 方案C：多轮对话数据

**原理：** 生成多轮对话的评测数据

**实现代码：**
```python
def generate_multi_turn_data() -> list[dict]:
    """生成多轮对话数据."""
    
    multi_turn_data = [
        {
            "turns": [
                {"role": "user", "content": "我买的手机屏幕碎了"},
                {"role": "assistant", "content": "我理解您的情况，请问您是想退货还是换货？"},
                {"role": "user", "content": "我想退货，但是已经过了7天"},
                {"role": "assistant", "content": "根据我们的政策..."}
            ],
            "expected_intent": "refund",
            "expected_risk_flags": ["policy_conflict"]
        }
    ]
    
    return multi_turn_data
```

**预期效果：**
- 生成30+个多轮对话case
- 覆盖对话上下文理解能力

---

## 四、实施计划

### 阶段一：知识库扩充（1周）

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 使用Synthesizer生成新文档 | 1天 | P0 |
| LLM生成补充文档 | 1天 | P0 |
| 人工审核和筛选 | 2天 | P0 |
| 导入知识库 | 0.5天 | P0 |
| 验证数据质量 | 0.5天 | P1 |

**里程碑：** 知识库达到300+条

### 阶段二：评测数据扩充（1周）

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 使用Synthesizer生成评测数据 | 1天 | P0 |
| 生成边界case | 1天 | P0 |
| 生成多轮对话数据 | 1天 | P1 |
| 人工审核和筛选 | 1天 | P0 |
| 保存为评测数据集 | 0.5天 | P0 |
| 验证数据质量 | 0.5天 | P1 |

**里程碑：** 评测数据达到300+条

### 阶段三：数据质量优化（1周）

| 任务 | 工作量 | 优先级 |
|------|--------|--------|
| 运行基线评测 | 0.5天 | P0 |
| 分析评测结果 | 0.5天 | P0 |
| 优化数据集 | 2天 | P0 |
| 重新评测 | 0.5天 | P0 |
| 文档更新 | 0.5天 | P1 |

**里程碑：** 数据质量达到要求

---

## 五、数据质量保证

### 5.1 数据质量检查清单

- [ ] **完整性** - 每条数据都有必要的字段
- [ ] **准确性** - 意图分类、风险标志正确
- [ ] **一致性** - 格式统一，命名规范
- [ ] **多样性** - 覆盖各种场景和边界case
- [ ] **真实性** - 数据符合实际业务场景

### 5.2 数据质量验证脚本

```python
def validate_dataset(dataset: list[dict]) -> dict:
    """验证数据集质量."""
    
    issues = []
    
    for i, item in enumerate(dataset):
        # 检查必要字段
        required_fields = ["input", "expected_intent", "ground_truth"]
        for field in required_fields:
            if field not in item:
                issues.append(f"Item {i}: Missing field '{field}'")
        
        # 检查意图分类
        valid_intents = ["refund", "return_exchange", "account_issue", 
                        "technical_issue", "product_consulting", 
                        "logistics", "complaint", "other"]
        if item.get("expected_intent") not in valid_intents:
            issues.append(f"Item {i}: Invalid intent '{item.get('expected_intent')}'")
        
        # 检查风险标志
        valid_risks = ["complaint_risk", "compensation_risk", "legal_risk",
                      "privacy_risk", "account_security_risk", "policy_conflict",
                      "insufficient_evidence", "low_confidence"]
        for risk in item.get("expected_risk_flags", []):
            if risk not in valid_risks:
                issues.append(f"Item {i}: Invalid risk flag '{risk}'")
    
    return {
        "total": len(dataset),
        "issues": issues,
        "passed": len(issues) == 0
    }
```

---

## 六、预期效果

### 6.1 数据量提升

| 维度 | 现状 | 目标 | 提升 |
|------|------|------|------|
| 知识库文档 | 106条 | 300+条 | +183% |
| 评测工单 | 101条 | 300+条 | +197% |
| 场景覆盖 | 12种 | 20+种 | +67% |
| 风险覆盖 | 8种 | 10+种 | +25% |

### 6.2 评测可信度提升

| 维度 | 现状 | 目标 | 提升 |
|------|------|------|------|
| 测试用例数 | 101条 | 300+条 | 统计显著性提升 |
| 场景覆盖 | 12种 | 20+种 | 覆盖更全面 |
| 边界case | 少 | 50+条 | 鲁棒性提升 |
| 多轮对话 | 无 | 30+条 | 上下文理解提升 |

---

## 七、风险与对策

| 风险 | 影响 | 对策 |
|------|------|------|
| 生成数据质量差 | 评测结果不准确 | 人工审核，迭代优化 |
| 数据重复 | 数据集冗余 | 去重处理 |
| 场景覆盖不全 | 评测不全面 | 专项补充边界case |
| 数据格式不一致 | 集成困难 | 统一格式规范 |

---

## 八、验收标准

### 8.1 数据量验收

- [ ] 知识库文档 ≥ 300条
- [ ] 评测工单 ≥ 300条
- [ ] 场景覆盖 ≥ 20种
- [ ] 风险覆盖 ≥ 10种

### 8.2 数据质量验收

- [ ] 数据完整性检查通过
- [ ] 数据准确性检查通过
- [ ] 数据一致性检查通过
- [ ] 数据多样性检查通过

### 8.3 评测效果验收

- [ ] 基线评测完成
- [ ] 评测报告生成
- [ ] 核心指标达到目标值

---

## 九、下一步行动

1. **确认方案** - 用户确认扩充方案
2. **实施阶段一** - 知识库扩充
3. **实施阶段二** - 评测数据扩充
4. **实施阶段三** - 数据质量优化
5. **运行评测** - 验证扩充效果

---

**方案完成时间：** 2026-05-29  
**预计完成时间：** 2026-06-19（3周）  
**负责人：** Hermes Agent + 用户确认
