# TicketPilot 基础设施修复：编码安全 + 评测稳定性 + 优化器策略升级

> **目标执行者**：任何 LLM（包括低级别模型），不需要理解项目全貌，逐步执行即可。
> **⚠️ 最后一次审查 (2026-06-11) 发现以下重要修复已应用到计划中：**
> - CRIT-1: Task 2 `submitted_at` 类型修复（str→datetime.fromisoformat）
> - CRIT-2: Task 4 `test_keyword_search_handles_special_chars` 移到 `tests/integration/`（带 DB skip 标记）
> - CRIT-3: Task 4 新增可单元测试的 `safe_content()` 辅助函数 + 重构测试
> - IMP-1: Task 1 `_like_search` 添加完整代码示例
> - IMP-2/3: 简化编码安全逻辑（去重 encode/decode + 去重 client_encoding）
> - IMP-4/5: Task 3 分类器 `continue`→`break` + PRIORITY_ORDER 移到模块级
> - IMP-6: 添加 regex 格式依赖注释
> - MIN-3/5: 重复常量复用 + 注释修正
> **总估时**：约 3-4 小时（含测试运行）
> **前置条件**：Python 3.11+，`uv` 已安装，工作目录为 `/home/hermes/ticketpilot`

---

## 背景（必读）

当前 TicketPilot 有三个基础设施问题阻塞了优化器的正常工作：

1. **FTS UnicodeDecodeError**：部分工单的 evidence retrieval 阶段因 UTF-8 解码失败而降级为空结果。错误信息：`UnicodeDecodeError: 'utf-8' codec can't decode byte 0xe2 in position 1: unexpected end of data`。可能发生在数据库返回的 content 字段或 CSV 数据加载过程中。
2. **评测不稳定**：相同输入、相同代码产生 ±1-2% 的波动，导致优化器的"修复后评测分数低于基线则回滚"策略误判微小改进为无改进。
3. **优化器修复策略单一**：只会加关键词，而分类器使用 first-match-wins 机制（REFUND > RETURN_EXCHANGE > ACCOUNT > ... > COMPLAINT > OTHER），往后面规则加关键词不会生效。

---

## Task 1：在各数据入口加编码安全防护

**目标**：确保所有读取文本的环节都不会因编码问题而崩溃或丢失数据。

### Step 1: 修改 `retrieve_evidence.py` — 检索结果内容安全处理

**文件**: `src/ticketpilot/retrieval/retrieve_evidence.py`

在 `retrieve_evidence()` 函数末尾，对返回的 candidates 做内容安全处理。

找到这个函数（第 16-45 行），把最后几行改成下面这样：

```python
def retrieve_evidence(
    normalized_text: str,
    intent: IntentClass,
    risk_flags: set[RiskFlag],
    top_k: int = 10,
    doc_types: list[DocType] | None = None,
    embedding_provider: Optional[FakeEmbeddingProvider] = None,
    enable_query_expansion: bool = False,
    reranker_config: Optional[RerankerConfig] = None,
) -> tuple[list[EvidenceCandidate], RetrievalTrace]:
    """Retrieve evidence candidates from the knowledge base."""
    query = build_retrieval_query(normalized_text, intent, risk_flags)
    trace = hybrid_retrieval(
        query=query,
        top_k=top_k,
        doc_types=doc_types,
        embedding_provider=embedding_provider,
        intent=intent.value if intent else None,
        enable_query_expansion=enable_query_expansion,
        reranker_config=reranker_config,
    )
    candidates = map_fused_to_evidence(trace.fused_results)
    
    # NEW: 安全处理每个 candidate 的内容，避免损坏的 UTF-8 导致下游崩溃
    for candidate in candidates:
        if hasattr(candidate, 'content') and candidate.content is not None:
            if isinstance(candidate.content, bytes):
                candidate.content = candidate.content.decode('utf-8', errors='replace')
    
    return candidates, trace
```

### Step 2: 修改 `keyword_search.py` — 数据库查询结果安全处理

**文件**: `src/ticketpilot/retrieval/keyword_search.py`

在 `_fts_search()` 函数中（第 70-169 行），找到第 154-167 行（处理查询结果的地方），在构造 KeywordResult 之前对 content 做安全处理。

把第 154-167 行改为：

```python
    results = []
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            for row in cur.fetchall():
                content_raw = row[3]
                # 安全处理：确保 content 是有效 str
                if content_raw is None:
                    safe_content = ""
                elif isinstance(content_raw, bytes):
                    safe_content = content_raw.decode('utf-8', errors='replace')
                else:
                    try:
                        safe_content = str(content_raw)
                        safe_content.encode('utf-8', errors='replace').decode('utf-8')
                    except Exception:
                        safe_content = "[content encoding error]"
                
                results.append(
                    KeywordResult(
                        chunk_id=row[0],
                        doc_id=row[1],
                        doc_type=DocType(row[2]),
                        content=safe_content,
                        score=float(row[4]),
                        rank=int(row[5]),
                        search_method="fts",
                        fts_rank=int(row[5]),
                        like_rank=None,
                    )
                )
```

### Step 2: 修改 `_like_search()` 的编码安全（完整代码）

**文件**: `src/ticketpilot/retrieval/keyword_search.py`

`_like_search()` 函数第 254-267 行，把 content 处理改为：

```python
            for row in cur.fetchall():
                content_raw = row[3]
                # 安全处理：确保 content 是有效 str
                if content_raw is None:
                    safe_content = ""
                elif isinstance(content_raw, bytes):
                    safe_content = content_raw.decode('utf-8', errors='replace')
                else:
                    try:
                        safe_content = str(content_raw)
                        safe_content.encode('utf-8', errors='replace').decode('utf-8')
                    except Exception:
                        safe_content = "[content encoding error]"

                results.append(
                    KeywordResult(
                        chunk_id=row[0],
                        doc_id=row[1],
                        doc_type=DocType(row[2]),
                        content=safe_content,
                        score=float(row[4]) if row[4] is not None else 0.0,
                        rank=int(row[5]),
                        search_method="like",
                        fts_rank=None,
                        like_rank=int(row[5]),
                    )
                )
```

### Step 3: 修改 `connection.py` — 数据库连接客户端编码设置

**文件**: `src/ticketpilot/retrieval/db/connection.py`

在 `get_db_pool()` 函数中，给连接字符串加上 `client_encoding` 参数。

找到第 51-54 行的 `conninfo` 赋值，改为：

```python
    conninfo = (
        f"host={DB_HOST} port={DB_PORT} dbname={DB_NAME} "
        f"user={DB_USER} password={DB_PASSWORD} "
        f"client_encoding=UTF8"
    )
```

### Step 4: 运行已有测试确保无回归

```bash
cd /home/hermes/ticketpilot
source .venv/bin/activate

# 运行关键字检索相关测试
python -m pytest tests/integration/test_keyword_retrieval.py -v

# 运行检索流水线测试
python -m pytest tests/integration/test_retrieval_pipeline.py -v

# 运行完整测试（如果 docker compose 可用）
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

**预期**：所有已有测试通过，没有新增失败。

### 验收标准

1. `retrieve_evidence()` 不再因编码异常的 content 抛出 UnicodeDecodeError
2. 数据库返回的 bytes 类型 content 被正确解码（使用 `errors='replace'`）
3. `_fts_search()` 和 `_like_search()` 对异常编码内容返回安全的空字符串或替换标记
4. 数据库连接强制使用 UTF-8 编码
5. 已有测试全部通过（`python -m pytest tests/integration/test_keyword_retrieval.py -v` 通过）

---

## Task 2：评测稳定性修复

**目标**：消除评测中 ±1-2% 的随机波动，确保相同输入产生完全相同输出。

### Step 1: 检查评测中的非确定性源

**首先执行这个命令**，查看评测是否有随机因素：

```bash
cd /home/hermes/ticketpilot
grep -rn "random\|shuffle\|seed\|deterministic\|hash.*time\|datetime.now" src/ticketpilot/evaluation/ src/ticketpilot/optimizer/evaluator.py | grep -v "test_\|__pycache__"
```

### Step 2: 修复 `predict_from_pipeline()` 中的非确定性时间戳

**文件**: `src/ticketpilot/evaluation/pipeline_predictions.py`

原因：每次调用 `predict_from_pipeline()` 都会创建 `datetime.now(timezone.utc)`，不同时间的评测会略有差异（主要影响 draft 相关指标）。

修改第 59-63 行：

```python
    # 使用固定时间戳以确保评测可重复
    # eval_ticket.submitted_at 是字符串（ISO 格式），需要转为 datetime
    submitted_at_raw = getattr(eval_ticket, 'submitted_at', None)
    if submitted_at_raw:
        try:
            submitted_at = datetime.fromisoformat(submitted_at_raw)
        except (ValueError, TypeError):
            submitted_at = datetime.now(timezone.utc)
    else:
        submitted_at = datetime.now(timezone.utc)

    raw_ticket = RawTicket(
        original_text=eval_ticket.original_text,
        submitted_at=submitted_at,
        customer_id=eval_ticket.customer_id,
    )
```

### Step 3: 检查 FakeEmbeddingProvider 是否完全确定性

```bash
cd /home/hermes/ticketpilot
cat src/ticketpilot/retrieval/providers/fake_embedding.py | head -80
```

确认：FakeEmbeddingProvider 应该基于 `hashlib.sha256(text.encode('utf-8'))` 生成伪随机向量，这已经是确定性的。

### Step 4: 验证评测可重复性

写一个快速验证脚本：

```bash
cd /home/hermes/ticketpilot
source .venv/bin/activate
python3 -c "
# 运行两次评测，比较结果是否一致
from ticketpilot.evaluation.loaders import load_eval_dataset
from ticketpilot.evaluation.pipeline_predictions import predict_from_pipeline
from ticketpilot.evaluation.metrics import compute_evaluation_summary

ds = load_eval_dataset('data/eval/tickets_eval.csv', 'data/eval/golden_expectations.csv').dataset

# 跑 2 次
preds1 = {cid: predict_from_pipeline(t) for cid, t in list(ds.tickets.items())[:5]}
preds2 = {cid: predict_from_pipeline(t) for cid, t in list(ds.tickets.items())[:5]}

# 比较
all_match = True
for cid in preds1:
    p1 = preds1[cid]
    p2 = preds2[cid]
    if p1.predicted_issue_type != p2.predicted_issue_type:
        print(f'MISMATCH: {cid} intent {p1.predicted_issue_type} vs {p2.predicted_issue_type}')
        all_match = False
    if p1.predicted_risk_flags != p2.predicted_risk_flags:
        print(f'MISMATCH: {cid} risk_flags {p1.predicted_risk_flags} vs {p2.predicted_risk_flags}')
        all_match = False
    if p1.predicted_severity != p2.predicted_severity:
        print(f'MISMATCH: {cid} severity {p1.predicted_severity} vs {p2.predicted_severity}')
        all_match = False

if all_match:
    print('ALL MATCH: 评测结果是确定性的 ✅')
else:
    print('MISMATCHES FOUND: 评测结果不一致 ❌')
"
```

### 验收标准

1. 前 5 条工单连续两次评测结果完全一致
2. 如果发现不一致，记录具体字段和不一致的根因

---

## Task 3：优化器修复策略升级 — 支持排除规则

**目标**：给优化器增加新修复类型 `exclusion_rule`，解决 first-match-wins 导致的"加关键词无效"问题。

### 背景

当前的分类系统是 `first-match-wins`：
```
REFUND → RETURN_EXCHANGE → ACCOUNT → TECHNICAL → PRODUCT → LOGISTICS → COMPLAINT → OTHER
```

如果一条工单说"我要退款但你们态度太差了"，`REFUND` 规则先匹配到"退款"，`COMPLAINT` 永远不会被触发。往 COMPLAINT 加关键词"态度差"也没用。

**解决方案**：给高优先级规则（如 REFUND）增加 exclusion rules，当排除条件命中时跳过 REFUND 规则，让匹配流转到 COMPLAINT。

### Step 1: 修改分类规则数据结构

**文件**: `src/ticketpilot/classification/rules.py`

给 `IntentRule` 添加 `exclusions` 字段：

```python
@dataclass
class IntentRule:
    """Rule for intent classification."""

    intent: IntentClass
    keywords: list[str]
    strong_indicator: str | None = None
    exclusions: list[str] | None = None  # NEW: 如果命中这些词，跳过此规则
```

### Step 2: 修改分类器支持排除规则

**文件**: `src/ticketpilot/classification/classifier.py`

在 `classify()` 方法的 Phase 2（first-match-wins）中，检查关键词命中后先看是否被排除。

找到第 61-74 行的匹配逻辑，改为：

```python
        for rule in self.rules:
            if rule.intent == IntentClass.OTHER:
                if rule.strong_indicator and rule.strong_indicator in text:
                    found_keyword_in_other = True
                continue
            for keyword in rule.keywords:
                if keyword in text:
                    # NEW: 检查排除规则 — 如果命中排除关键词，则跳过此规则
                    if rule.exclusions:
                        if any(excl in text for excl in rule.exclusions):
                            break  # 该规则被排除，跳出内层循环，match_count 保持 0

                    match_count += 1
                    matched_intent = rule.intent
                    matched_keyword_len = len(keyword)
                    break  # 退出内层循环
            if match_count > 0:
                break  # first-match-wins：退出外层循环
```

### Step 3: 给 COMPLAINT 关键词冲突的规则加排除词

**文件**: `src/ticketpilot/classification/rules.py`

修改 REFUND 规则，添加 `exclusions`：

找到第 20-25 行的 REFUND 规则，改为：

```python
    IntentRule(
        intent=IntentClass.REFUND,
        keywords=["退款", "申请退款", "退款请求", "退钱", "退费", "退押金",
                  "保价", "降价", "差价退还"],
        exclusions=["投诉", "态度", "差评", "12315", "维权", "消费者协会"],  # NEW
    ),
```

给 RETURN_EXCHANGE 也加排除词（第 26-30 行）：

```python
    IntentRule(
        intent=IntentClass.RETURN_EXCHANGE,
        keywords=["退货", "换货", "退换", "退货运费", "退货地址", "七天无理由",
                  "质量问题退", "发错货", "发错颜色", "保修期", "质保", "保修"],
        exclusions=["投诉", "态度", "差评", "12315"],  # NEW
    ),
```

### Step 4: 给 Fixer 添加 `exclusion_rule` 修复类型

**文件**: `src/ticketpilot/optimizer/fixer.py`

在 `Fixer` 类中添加新方法 `_fix_exclusion_rule`。

**注意**：`_CLASSIFICATION_RULES_PATH` 常量已在第 42 行定义（`_CLASSIFICATION_RULES_PATH = PROJECT_ROOT / "src" / "ticketpilot" / "classification" / "rules.py"`），无需重复定义。

在 `apply_fix()` 的 dispatch 字典中添加新条目（第 85-90 行）：

```python
        dispatch = {
            "confidence_threshold": self._fix_confidence_threshold,
            "confidence_weight": self._fix_confidence_threshold,
            "intent_keyword": self._fix_intent_keywords,
            "risk_keyword": self._fix_risk_keywords,
            "exclusion_rule": self._fix_exclusion_rule,  # NEW
        }
```

在文件末尾（第 399 行之后）添加新方法：

```python
    def _fix_exclusion_rule(self, diagnosis: Any) -> FixResult:
        """Add exclusion keywords to a high-priority IntentRule.

        Used when COMPLAINT cases are being absorbed by higher-priority
        rules like REFUND or RETURN_EXCHANGE due to first-match-wins.
        
        ``diagnosis.expected_values`` should contain:
            - ``"intent"``: the intent whose exclusion list to modify (e.g. "REFUND")
            - ``"predicted_intent"``: the intent that's incorrectly matching
        ``diagnosis.suggested_keywords``: keywords to add as exclusions.
        """
        intent_value = diagnosis.expected_values.get("intent")
        predicted_intent = diagnosis.expected_values.get("predicted_intent", "")
        keywords = getattr(diagnosis, "suggested_keywords", [])

        if not intent_value:
            return FixResult(
                success=False,
                fix_type="exclusion_rule",
                description="Missing 'intent' in expected_values",
                error="expected_values must contain 'intent'",
            )

        if not keywords:
            return FixResult(
                success=False,
                fix_type="exclusion_rule",
                description="No exclusion keywords to add",
                error="suggested_keywords is empty",
            )

        file_path = str(_CLASSIFICATION_RULES_PATH)
        self._backup_file(file_path)

        if self.dry_run:
            return FixResult(
                success=True,
                fix_type="exclusion_rule",
                description=f"[dry-run] Would add exclusions {keywords!r} to {intent_value} rule",
                files_modified=[file_path],
            )

        source = Path(file_path).read_text(encoding="utf-8")

        # 定位目标 intent 的 IntentRule
        # 我们找的是 predicted_intent 所在的高优先级规则块
        # 因为 COMPLAINT 被 REFUND 抢走时，需要修改 REFUND 的 exclusions
        target_intent = predicted_intent if predicted_intent else intent_value
        
        intent_pattern = rf"intent=IntentClass\.{target_intent}\b"
        intent_match = re.search(intent_pattern, source)
        if not intent_match:
            return FixResult(
                success=False,
                fix_type="exclusion_rule",
                description=f"IntentClass.{target_intent} not found in rules",
                error=f"intent '{target_intent}' not found in {file_path}",
            )

        search_start = intent_match.start()
        
        # 检查是否已经有 exclusions 字段
        excl_pattern = r'exclusions=\[(.*?)\]'
        excl_match = re.search(excl_pattern, source[search_start:], re.DOTALL)
        
        if excl_match:
            # 已有 exclusions，追加
            excl_body = excl_match.group(1).strip()
            existing_excl: list[str] = []
            if excl_body:
                existing_excl = [m.group(1) for m in re.finditer(r'"([^"]+)"', excl_body)]
            new_only = [kw for kw in keywords if kw not in existing_excl]
            if not new_only:
                return FixResult(
                    success=True,
                    fix_type="exclusion_rule",
                    description=f"All exclusions already present in {target_intent}",
                    files_modified=[file_path],
                )
            all_excl = existing_excl + new_only
            excl_entries = ", ".join(f'"{kw}"' for kw in all_excl)
            new_excl_block = f"exclusions=[{excl_entries}]"
            
            abs_start = search_start + excl_match.start()
            abs_end = search_start + excl_match.end()
            new_source = source[:abs_start] + new_excl_block + source[abs_end:]
        else:
            # 没有 exclusions 字段，在 keywords 列表之后插入
            # 注意：这个 regex 假设 IntentRule 的 keywords= 后面跟逗号和其他字段
            # 即 format 为 keywords=[...],\n       其他字段
            # 如果 rules.py 格式变化（如末尾字段无逗号），需要调整此 regex
            kw_list_pattern = r'keywords=\[(.*?)\](.*?,)'
            kw_match = re.search(kw_list_pattern, source[search_start:], re.DOTALL)
            if not kw_match:
                return FixResult(
                    success=False,
                    fix_type="exclusion_rule",
                    description="Could not locate keywords list",
                    error="keywords=[...] not found",
                )
            
            kw_end = search_start + kw_match.end()
            excl_entries = ", ".join(f'"{kw}"' for kw in keywords)
            insertion = f',\n        exclusions=[{excl_entries}],'
            
            # 找到 keywords 行后面的内容插入位置
            new_source = source[:kw_end] + insertion + source[kw_end:]

        self._write_file(file_path, new_source)

        return FixResult(
            success=True,
            fix_type="exclusion_rule",
            description=f"Added {len(keywords)} exclusion(s) to {target_intent}: {keywords}",
            files_modified=[file_path],
        )
```

### Step 5: 更新 config.py 中的 FIX_PRIORITY

**文件**: `src/ticketpilot/optimizer/config.py`

在第 32-40 行添加新类型：

```python
FIX_PRIORITY = {
    "confidence_threshold": 1,
    "confidence_weight": 1,
    "intent_keyword": 2,
    "risk_keyword": 2,
    "exclusion_rule": 2,  # NEW: same priority as keyword fixes
    "reranker_weight": 3,
    "knowledge_addition": 4,
    "code_change": 5,
}
```

### Step 6: 更新 DiagnosticsEngine 以生成 exclusion_rule 修复

**文件**: `src/ticketpilot/optimizer/diagnostics.py`

在文件顶部（第 1-18 行，`from __future__ import annotations` 之后）添加常量：

```python
# 意图优先级顺序（first-match-wins）
PRIORITY_ORDER = [
    "REFUND", "RETURN_EXCHANGE", "ACCOUNT_ISSUE",
    "TECHNICAL_ISSUE", "PRODUCT_CONSULTING", "LOGISTICS",
    "COMPLAINT", "OTHER"
]
```

在 `analyze()` 方法的 intent 分析部分（第 433-475 行），对于 COMPLAINT 被高优先级规则抢走的情况，生成 `exclusion_rule` 类型的修复。

在第 461-475 行（构造 Diagnosis 对象的地方），在 `all_diagnoses.append(Diagnosis(...))` 之前插入逻辑：

```python
            # 决定使用哪种修复策略
            fix_type = "intent_keyword"

            # 新增逻辑：如果 predicted intent 的优先级高于 expected intent
            # 说明是 first-match-wins 问题，应该用 exclusion_rule
            if expected.upper() in PRIORITY_ORDER and predicted.upper() in PRIORITY_ORDER:
                expected_prio = PRIORITY_ORDER.index(expected.upper())
                predicted_prio = PRIORITY_ORDER.index(predicted.upper())
                if predicted_prio < expected_prio:
                    # predicted intent 优先级更高，是 first-match-wins 问题
                    # 使用 exclusion_rule 在 predicted intent 上加排除词
                    fix_type = "exclusion_rule"
```

然后把传给 Diagnosis 的 `suggested_fix_type` 改成使用变量 `fix_type`：

找到第 467 行：

```python
            suggested_fix_type="intent_keyword",
```
改为：
```python
            suggested_fix_type=fix_type,
```

### Step 7: 运行完整测试

```bash
cd /home/hermes/ticketpilot
source .venv/bin/activate

# 单元测试（不需要数据库）
python -m pytest tests/unit/ -v --tb=short 2>&1 | tail -20

# 分类器测试
python -m pytest tests/ -k "classif" -v --tb=short 2>&1

# 全部测试（需要 docker compose up -d）
python -m pytest tests/ -v --tb=short 2>&1 | tail -40
```

### 验收标准

1. `IntentRule` 支持 `exclusions` 字段，向下兼容（老规则不加 exclusions 也正常工作）
2. 分类器在匹配规则时会检查排除词：如果关键词命中但排除词也命中，跳过该规则
3. REFUND 和 RETURN_EXCHANGE 规则有新排除词，如"投诉"、"态度"、"12315"
4. Fixer 可以执行 `exclusion_rule` 类型的修复（添加排除词到高优先级规则）
5. DiagnosticsEngine 能识别 first-match-wins 问题并生成 exclusion_rule 修复建议
6. 已有测试全部通过，无回归

---

## Task 4：新增测试

### 文件 1: `tests/unit/test_encoding_safety.py`（新建 — 不需要 DB）

```python
"""Tests for encoding safety and exclusion rules in classification.

All tests in this file run against the IntentClassifier (pure Python, no DB).
Encoding safety in the retrieval layer (keyword_search.py) requires DB
and is tested in tests/integration/.
"""

import pytest
from ticketpilot.schema.ticket import IntentClass
from ticketpilot.classification.classifier import IntentClassifier


class TestEncodingSafety:
    """Verify that the classifier handles bad input gracefully."""

    def test_bytes_content_safety(self):
        """Classifier should not crash on strings with embedded byte escapes."""
        classifier = IntentClassifier()
        # 包含可能损坏编码的文本
        result = classifier.classify("退款\\xe2\\x80\\x99投诉")
        assert result.intent is not None

    def test_null_content_safety(self):
        """Null/empty content should result in OTHER classification."""
        classifier = IntentClassifier()
        result = classifier.classify("")
        assert result.intent == IntentClass.OTHER
        assert result.confidence > 0

    def test_surrogate_characters(self):
        """Classifier should not crash on surrogate characters in Python strings."""
        classifier = IntentClassifier()
        text = "退款问题\\ud800态度差"
        result = classifier.classify(text)
        assert result.intent is not None


class TestExclusionRules:
    """Verify that exclusion rules work correctly in classifier."""

    def test_refund_excluded_for_complaint(self):
        """退款 + 投诉 → 应为 COMPLAINT，不是 REFUND。"""
        classifier = IntentClassifier()
        result = classifier.classify("我要退款，你们态度太差了我要投诉")
        # 因为 REFUND 规则有 exclusions=["投诉", "态度"]
        # 所以应该跳过 REFUND，匹配到 COMPLAINT
        assert result.intent == IntentClass.COMPLAINT

    def test_refund_without_exclusion(self):
        """仅退款，无投诉关键词 → 应为 REFUND。"""
        classifier = IntentClassifier()
        result = classifier.classify("我要退款")
        assert result.intent == IntentClass.REFUND

    def test_return_excluded_for_complaint(self):
        """退货 + 态度差 → 应为 COMPLAINT。"""
        classifier = IntentClassifier()
        result = classifier.classify("我要退货，你们客服态度太恶心了")
        # RETURN_EXCHANGE 有 exclusions=["投诉", "态度", "差评", "12315"]
        assert result.intent == IntentClass.COMPLAINT

    def test_refund_not_blocked_by_irrelevant_word(self):
        """包含不在排除列表中的词 → 仍为 REFUND。"""
        classifier = IntentClassifier()
        # "退款"匹配，且"热线"不在 REFUND 排除列表中
        result = classifier.classify("我要退款但你们热线打不通")
        assert result.intent == IntentClass.REFUND

    def test_refund_excluded_when_complaint_keyword_present(self):
        """退款 + 12315 → 排除规则生效 → 变为 COMPLAINT。"""
        classifier = IntentClassifier()
        # "12315" 在 REFUND exclusions 中 -> 跳过 REFUND -> COMPLAINT 匹配
        result = classifier.classify("我要退款，我的订单号是12315")
        assert result.intent == IntentClass.COMPLAINT
```

### 文件 2: `tests/integration/test_encoding_safety_db.py`（新建 — 需要 DB）

```python
"""Integration tests for encoding safety in DB-backed retrieval.

Requires PostgreSQL (Docker). Skipped when TICKETPILOT_SKIP_DB_TESTS=1.
"""

import os

import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("TICKETPILOT_SKIP_DB_TESTS") == "1",
    reason="Skipping DB-dependent integration tests",
)


class TestFTSContentSafety:
    """Verify FTS search handles encoding edge cases (needs real DB connection)."""

    def test_keyword_search_handles_special_chars(self):
        """Keyword search should handle special characters without crashing."""
        from ticketpilot.retrieval.keyword_search import _fts_search

        results = _fts_search("退款\\x00投诉", top_k=5)
        # 不应崩溃
        assert isinstance(results, list)
```

### 运行测试

```bash
cd /home/hermes/ticketpilot
source .venv/bin/activate

# 单元测试（不需要 DB）
python -m pytest tests/unit/test_encoding_safety.py -v --tb=short

# 集成测试（需要 DB）
python -m pytest tests/integration/test_encoding_safety_db.py -v --tb=short

# 全部单元测试
python -m pytest tests/unit/ -v --tb=short 2>&1 | tail -20
```

### 验收标准

1. `test_refund_excluded_for_complaint` 通过：退款+投诉被正确分类为 COMPLAINT
2. `test_refund_without_exclusion` 通过：仅退款仍为 REFUND
3. `test_return_excluded_for_complaint` 通过：退货+态度差为 COMPLAINT
4. 编码安全单元测试通过（classifier 对异常输入不崩溃）
5. 集成测试 `test_keyword_search_handles_special_chars` 在 DB 可用时通过，DB 不可用时被 SKIP
6. 全部单元测试无回归

---

## 执行顺序和提交策略

```
Task 1 (编码安全) → git commit → Task 2 (评测稳定性) → git commit
→ Task 3 (排除规则) → git commit → Task 4 (新测试) → git commit
```

每次 commit 格式：
```bash
git add [修改的文件]
git commit -m "fix: [简短描述]"
```

全部完成后：
```bash
# 运行完整测试套件
python -m pytest tests/ -v --tb=short 2>&1 | tail -40

# 确认无回归
echo "总测试数: $(python -m pytest tests/ --co -q 2>&1 | tail -1)"
```

## 回滚步骤

如果任何步骤出问题：
1. 如果只是某个 task 的修改有问题：`git checkout -- [文件路径]` 恢复该文件
2. 如果要回滚整个 session：`git reset --hard HEAD~N`（N 为已提交的次数）
3. 优化器本身有自动回滚机制：修改后的规则如果导致评测分数下降，会自动恢复

## 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|---------|---------|
| 测试需要数据库 | Docker 未启动 | `docker compose up -d` |
| import 错误 | venv 未激活 | `source .venv/bin/activate` |
| intent pattern 找不到 | 枚举名不匹配 | 检查 `IntentClass` 枚举的实际值 |
| exclusion_rule fix 失败 | regex 不匹配源码格式 | 查看 rules.py 实际格式，调整正则 |
| 测试 `test_refund_excluded_for_complaint` 失败 | 排除规则未生效 | 确认 classifer.py 中的排除逻辑正确插入 |
