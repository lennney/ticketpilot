# Jieba Chinese Keyword Extraction — Implementation Plan

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Replace n-gram-based Chinese keyword extraction with jieba word segmentation so the optimizer can extract meaningful Chinese keywords (e.g. `"投诉"`, `"态度"`, `"赔付"`) instead of garbage n-grams (e.g. `"我要"`, `"们的"`, `"货但"`).

**Architecture:** Inject jieba into two existing functions in `diagnostics.py` — `_extract_chinese_keywords()` (document-frequency keyword extraction) and the inner `_cjk_ngrams()` helper inside `_analyze_causal_features()` (lift-based causal feature extraction). The function signatures and callers stay identical; only the internal word-splitting logic changes.

**Tech Stack:** jieba (MIT license, std Chinese NLP lib), Python 3.11+, pytest

**Status:** Plan started 2026-06-11, started 2026-06-11

---

### Task 1: Add jieba dependency and verify installation

**Objective:** Install jieba as a dev dependency (not a core dep — only used by optimizer diagnostics).

**Files:**
- Modify: `pyproject.toml` (add jieba to dev dependencies)
- No tests needed for this task

**Step 1:** Add jieba to the `[dependency-groups]` -> `dev` section in `pyproject.toml`

Current dev dependencies:
```toml
[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "pytest-cov>=7.0.0",
    "ruff>=0.15.12",
]
```

Change to:
```toml
[dependency-groups]
dev = [
    "pytest>=9.0.3",
    "pytest-cov>=7.0.0",
    "ruff>=0.15.12",
    "jieba>=0.42.1",
]
```

**Step 2:** Install and verify

```bash
cd ~/ticketpilot
uv add --dev jieba>=0.42.1
.venv/bin/python -c "import jieba; print(jieba.__version__)"
```
Expected: `0.42.1`

**Step 3:** Verify jieba behaves correctly for our use case

```bash
.venv/bin/python -c "
import jieba
# Should produce meaningful words, not n-gram garbage
print(jieba.lcut('我要退货加赔偿'))
# Expected: ['我', '要', '退货', '加', '赔偿']
print(jieba.lcut('投诉客服态度太差了'))
# Expected: meaningful words like ['投诉', '客服', '态度', '太差', '了']
"
```

---

### Task 2: Rewrite `_extract_chinese_keywords()` with jieba

**Objective:** Replace the n-gram-based `_extract_chinese_keywords()` with a jieba-based version that extracts proper Chinese words by document frequency.

**Files:**
- Modify: `src/ticketpilot/optimizer/diagnostics.py` (~lines 169-218)
- Test: `tests/unit/test_optimizer_diagnostics_keywords.py` (update assertions)

**Design:**

The new function:
1. For each text, use `jieba.lcut(text)` to get proper words
2. Filter out: stop words, single-character words, existing keywords, non-Chinese tokens
3. Count document frequency (how many texts contain each word)
4. Filter out words appearing in >50% of texts (too generic)
5. Return top N by document frequency

**Step 1:** Write failing tests first (update keyword tests)

The existing tests in `test_optimizer_diagnostics_keywords.py` are already abstract enough to work with jieba (they check type, len, not-in-existing). But the test `test_extract_chinese_keywords_stop_words_filtered` uses `"我是好人", "你好吗"` which jieba segments as `['我', '是', '好人', '你', '好吗']`. With single-char filtering, "好" shouldn't appear. Let me check what jieba actually outputs:

```python
jieba.lcut("我是好人")  # → ['我', '是', '好人']
jieba.lcut("你好吗")     # → ['你', '好吗'] or ['你', '好', '吗']
```

The test is already abstract enough (`assert isinstance(keywords, list)`) — it should pass. But I should also add test `test_extract_jieba_returns_meaningful_words` to verify jieba actually works.

Add one new test:
```python
def test_extract_jieba_returns_meaningful_words():
    """Test that jieba produces proper Chinese words (not broken n-grams)."""
    from ticketpilot.optimizer.diagnostics import _extract_chinese_keywords

    texts = [
        "我要投诉你们客服态度太差了",
        "投诉服务不好态度恶劣",
    ]
    keywords = _extract_chinese_keywords(texts, [])
    # Should contain meaningful words, not n-gram artifacts
    for kw in keywords:
        # Each keyword should be at least 2 chars
        assert len(kw) >= 2
        # Should not be a mid-word split (like '货但', '们的')
        # We can't assert exact output since jieba version varies,
        # but '投诉' should definitely be a top keyword
    assert "投诉" in keywords, "投诉 should be in extracted keywords"
```

**Step 2:** Run existing tests to verify they still fail as expected

Run: `.venv/bin/python -m pytest tests/unit/test_optimizer_diagnostics_keywords.py -v`
Expected: All pass (these tests are abstract enough to work with any implementation)

Actually the existing tests might already pass since they use abstract assertions. Let me proceed to the implementation.

**Step 3:** Replace `_extract_chinese_keywords()` body

Old code (lines 169-218):
```python
def _extract_chinese_keywords(
    texts: list[str],
    existing_keywords: list[str],
    max_keywords: int = 5,
) -> list[str]:
    """..."""
    if not texts:
        return []

    existing_set = set(existing_keywords)
    word_counter: Counter[str] = Counter()

    for text in texts:
        # Extract only CJK characters
        cjk_only = re.sub(r"[^\u4e00-\u9fff]", "", text)
        if len(cjk_only) < 2:
            continue

        seen_in_text: set[str] = set()
        for ngram_len in (2, 3, 4):
            for i in range(len(cjk_only) - ngram_len + 1):
                ngram = cjk_only[i : i + ngram_len]
                if ngram in existing_set or ngram in _CHINESE_STOP_WORDS:
                    continue
                if ngram not in seen_in_text:
                    seen_in_text.add(ngram)
                    word_counter[ngram] += 1

    threshold = len(texts) * 0.5
    filtered = [(w, c) for w, c in word_counter.most_common() if c <= threshold]
    return [word for word, _ in filtered[:max_keywords]]
```

New code:
```python
import jieba

def _extract_chinese_keywords(
    texts: list[str],
    existing_keywords: list[str],
    max_keywords: int = 5,
) -> list[str]:
    """Extract frequent Chinese keywords from ticket texts.

    Uses jieba word segmentation to tokenize Chinese text into proper
    words, then ranks by document frequency. Much more accurate than
    the previous n-gram approach which produced meaningless fragments.

    Args:
        texts: List of Chinese ticket texts to analyze.
        existing_keywords: Keywords already present in the rule (to exclude).
        max_keywords: Maximum number of new keywords to return.

    Returns:
        List of up to ``max_keywords`` new Chinese keyword strings,
        sorted by frequency (most frequent first).
    """
    if not texts:
        return []

    existing_set = set(existing_keywords)
    word_counter: Counter[str] = Counter()

    for text in texts:
        # Skip very short texts
        if len(text.strip()) < 2:
            continue

        # Tokenize with jieba (precise mode)
        words = jieba.lcut(text)
        seen_in_text: set[str] = set()

        for word in words:
            # Skip: single characters, stop words, existing keywords,
            # non-Chinese tokens (pure ASCII), very long tokens (likely noise)
            word = word.strip()
            if len(word) < 2:
                continue
            if word in existing_set:
                continue
            if word in _CHINESE_STOP_WORDS:
                continue
            if word.isascii():
                continue
            # Count each word at most once per text (document frequency)
            if word not in seen_in_text:
                seen_in_text.add(word)
                word_counter[word] += 1

    # Filter out words that appear in >50% of texts (too generic)
    threshold = len(texts) * 0.5
    filtered = [(w, c) for w, c in word_counter.most_common() if c <= threshold]

    # Return top keywords by frequency
    return [word for word, _ in filtered[:max_keywords]]
```

NOTE: Add `import jieba` after line 10 (`from collections import Counter`) in `diagnostics.py`. Do NOT import `jieba.analyse` — it's not needed and would violate YAGNI.

**Step 4:** Run tests to verify pass

Run: `.venv/bin/python -m pytest tests/unit/test_optimizer_diagnostics_keywords.py -v`
Expected: All 8 tests pass

Run: `.venv/bin/python -m pytest tests/unit/test_optimizer_diagnostics.py -v`
Expected: All 18 tests still pass (no changes needed for keywords in these)

**Acceptance Criteria:**
1. `jieba.lcut("我要退货加赔偿")` returns `['我', '要', '退货', '加', '赔偿']` (proper words, not n-grams)
2. `_extract_chinese_keywords(["我要投诉你们客服态度太差了"], [])` returns `['投诉', '客服', '态度']` or similar meaningful words
3. All 8 keyword extraction tests pass
4. No regressions in diagnostics tests (18/18 pass)

---

### Task 3: Rewrite `_cjk_ngrams()` in `_analyze_causal_features()` with jieba

**Objective:** Replace the n-gram-based inner `_cjk_ngrams()` function with jieba-based word frequency extraction for lift analysis.

**Files:**
- Modify: `src/ticketpilot/optimizer/diagnostics.py` (~lines 254-286, the `_cjk_ngrams` definition and lift computation)
- Test: `tests/unit/test_optimizer_engine.py` (~lines 559-614, `TestAnalyzeCausalFeatures`)

**Step 1:** Add test for jieba word extraction in causal analysis

Add this test after `test_existing_keywords_filtered` in `test_optimizer_engine.py`:

```python
def test_causal_returns_jieba_words_not_ngrams(self):
    \"\"\"Verifies causal features are proper jieba words, not n-gram artifacts.\"\"\"
    from ticketpilot.optimizer.diagnostics import _analyze_causal_features

    # Text with clear distinguishing keywords + a first-match-wins pattern
    mis = [
        "我要投诉你们客服态度太差了，申请退款因为服务不好",
        "服务态度恶劣我要投诉，退款不退就算了",
    ]
    correct = [
        "申请退款订单号12345请尽快处理",
        "我要申请退款，订单号67890",
    ]
    result = _analyze_causal_features(mis, correct, [\"退款\"], max_features=3)
    assert isinstance(result, list)
    assert len(result) > 0
    # \"投诉\" and \"态度\" should be distinguishing features (in mis but not in correct)
    # \"退款\" should NOT appear (in existing_keywords)
    assert \"退款\" not in result
    # Keywords should be proper Chinese words, not n-gram fragments
    for kw in result:
        assert len(kw) >= 2  # at least 2 chars
        # Should NOT be mid-word splits like '货但', '们的', '我申'
        assert kw in \"投诉态度恶劣客服太差退款服务订单处理\".replace(\"退款\", \"\"), \
            f\"'{kw}' doesn't look like a real Chinese word\"
```

**Step 2:** Verify new test fails... actually it might pass since the assertions are abstract. Let's proceed to implementation.

**Step 3:** Replace the `_cjk_ngrams` definition inside `_analyze_causal_features`

Replace `_cjk_ngrams` definition inside `_analyze_causal_features`.

Old code (lines 256-269):
```python
    def _cjk_ngrams(texts: list[str]) -> Counter:
        counter: Counter[str] = Counter()
        for text in texts:
            cjk = re.sub(r"[^\u4e00-\u9fff]", "", text)
            seen: set[str] = set()
            for n in (2, 3, 4):
                for i in range(len(cjk) - n + 1):
                    gram = cjk[i:i + n]
                    if gram in existing_set:
                        continue
                    if gram not in seen:
                        seen.add(gram)
                        counter[gram] += 1
        return counter
```

New code:
```python
    def _jieba_words(texts: list[str]) -> Counter:
        counter: Counter[str] = Counter()
        for text in texts:
            if len(text.strip()) < 2:
                continue
            words = jieba.lcut(text)
            seen: set[str] = set()
            for word in words:
                word = word.strip()
                if len(word) < 2:
                    continue
                if word in existing_set:
                    continue
                if word in _CHINESE_STOP_WORDS:
                    continue
                if word in seen:
                    continue
                seen.add(word)
                counter[word] += 1
        return counter
```

**Step 3:** Update the call sites in `_analyze_causal_features`

Replace (line 271-272):
```python
    mis_counter = _cjk_ngrams(misclassified_texts)
    correct_counter = _cjk_ngrams(correctly_classified_texts)
```

With:
```python
    mis_counter = _jieba_words(misclassified_texts)
    correct_counter = _jieba_words(correctly_classified_texts)
```

**Step 4:** Run tests to verify

Run: `.venv/bin/python -m pytest tests/unit/test_optimizer_engine.py::TestAnalyzeCausalFeatures -v`
Expected: All 5 tests pass

Run: Full optimizer test suite:
`.venv/bin/python -m pytest tests/unit/test_optimizer_*.py -q --tb=short`
Expected: 121+ passed (no regressions)

**Acceptance Criteria:**
1. `_analyze_causal_features` uses jieba instead of n-grams internally
2. All 5 causal feature tests pass
3. Full optimizer test suite passes with no regressions

---

### Task 4: Install jieba in venv and run full validation

**Objective:** Ensure jieba is actually installed and run the complete optimizer test suite.

**Step 1:** Install jieba

```bash
cd ~/ticketpilot
uv add --dev jieba>=0.42.1
```

Expected: Success

**Step 2:** Run full optimizer test suite

```bash
.venv/bin/python -m pytest tests/unit/test_optimizer_*.py -v --tb=short
```

Expected: All tests pass (keyword extraction tests + diagnostics + engine + fixer + etc.)

**Step 3:** Run full project test suite (unit tests only, no DB)

```bash
.venv/bin/python -m pytest tests/unit/ -q --tb=short 2>&1 | tail -5
```

Expected: No regressions beyond pre-existing failures

**Acceptance Criteria:**
1. jieba `0.42.1+` installed in venv
2. All optimizer tests pass
3. All unit tests pass (no regressions)

---

### Task 5: Run optimizer diagnose-only to verify real improvement

**Objective:** Verify that jieba produces meaningful Chinese keywords in a real optimizer run.

**Step 1:** Run diagnose-only

```bash
cd ~/ticketpilot
.venv/bin/python -m ticketpilot.optimizer --diagnose-only --rounds 1 2>&1 | grep -E "kws=|gain=|fix=" | head -10
```

Expected: The suggested keywords should now be meaningful Chinese words like `投诉`, `态度`, `客服`, `赔偿`, `退款` instead of n-gram garbage like `我要`, `们的`, `货但`.

**Acceptance Criteria:**
1. No n-gram artifacts (no `'我要'`, `'们的'`, `'货但'`) in suggested keywords
2. Keywords are proper Chinese words (2-4 chars, meaningful)
3. Top keywords include domain-relevant terms (投诉, 态度, 退款, 等等)
