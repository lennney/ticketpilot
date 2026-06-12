# Scoring-Based Intent Classifier

> **Goal:** Replace first-match-wins with keyword scoring to fix the root cause of optimizer stagnation and improve multi-intent handling.
>
> **Run all commands from project root (`/home/hermes/ticketpilot/`). Activate venv first: `source .venv/bin/activate`.**

## Architecture

**Current:** Phase 2 iterates rules in priority order (REFUND > RETURN_EXCHANGE > ... > COMPLAINT). First rule with a matching keyword wins — adds keyword TO that rule may not help if a higher-priority rule catches the ticket first.

**New:** Score every intent (except OTHER) by counting matching keywords. Apply exclusion penalties. Highest score wins. Tiebreaker = priority order.

This change means:
1. Adding keywords to any rule directly raises its score — fixes the optimizer
2. Multi-intent text (e.g. "退款投诉态度差") scores BOTH refund and complaint; complaint wins if it has more matches
3. Exclusions become penalties, not complete blocks — better for edge cases

**Tech Stack:** Python 3.11+, no new dependencies

---

### Task 1: Score-based classification logic

**Objective:** Replace Phase 2 first-match-wins with scoring in `classifier.py`.

**Files:**
- Modify: `src/ticketpilot/classification/classifier.py` (lines 55-103)
- Test: `tests/unit/test_classification.py`

**New scoring algorithm (add to class, below `classify()`):**

```python
def _score_intents(self, text: str) -> dict[str, float]:
    """Score each intent (except OTHER) by keyword matches with exclusion penalties.

    Returns dict like {"refund": 4.0, "complaint": 2.0, ...}.
    """
    scores: dict[str, float] = {}
    for rule in self.rules:
        if rule.intent == IntentClass.OTHER:
            continue
        score = 0.0
        for keyword in rule.keywords:
            if keyword in text:
                score += len(keyword)  # longer keywords = stronger signal
        if rule.exclusions:
            for excl in rule.exclusions:
                if excl in text:
                    score -= len(excl)  # exclusion penalty
        scores[rule.intent.value] = max(0.0, score)
    return scores
```

**Changes to `classify()` method:**

1. Phase 1 (strong indicators) — **unchanged**, still fast path
2. Phase 2 — replace entire old block (lines 55-103) with scoring code that includes its own `return ClassificationResult(...)`:
   - Call `_score_intents(text)`
   - Sort by score desc, then rule priority for ties
   - If top_score <= 0: return OTHER with WEAK_CONFIDENCE
   - Confidence: margin = (top_score - second_score) / top_score
     - margin >= 0.50: CONFIDENCE_HIGH (0.78)
     - margin >= 0.25: CONFIDENCE_MEDIUM (0.60)
     - else: WEAK_CONFIDENCE (0.50)
   - Return `ClassificationResult(intent=top_intent, confidence=..., classified_at=...)`
3. **Clean up unused imports**: Remove `CONFIDENCE_KEYWORD_1CHAR`, `CONFIDENCE_KEYWORD_LONG_TEXT`, `CONFIDENCE_KEYWORD_WITH_ORDER` from the import in classifier.py (no longer used by new confidence logic).
4. The old `found_keyword_in_other` / `matched_keyword_len` / `match_count` variables and the old `return` statement are entirely removed.

**Complete replacement code for lines 55-103:**

```python
        # Phase 2: Score-based intent classification
        scores = self._score_intents(text)

        if not scores:
            return ClassificationResult(
                intent=IntentClass.OTHER,
                confidence=WEAK_CONFIDENCE,
                classified_at=datetime.now(timezone.utc),
            )

        # Sort by score desc, then rule priority (position in INTENT_RULES) for ties
        priority_order = {rule.intent.value: i for i, rule in enumerate(self.rules)}
        ranked = sorted(
            scores.items(),
            key=lambda x: (-x[1], priority_order.get(x[0], 999)),
        )
        top_intent_str, top_score = ranked[0]

        if top_score <= 0:
            return ClassificationResult(
                intent=IntentClass.OTHER,
                confidence=WEAK_CONFIDENCE,
                classified_at=datetime.now(timezone.utc),
            )

        matched_intent = IntentClass(top_intent_str)
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        margin = (top_score - second_score) / top_score

        if margin >= 0.5:
            confidence = CONFIDENCE_HIGH
        elif margin >= 0.25:
            confidence = CONFIDENCE_MEDIUM
        else:
            confidence = WEAK_CONFIDENCE

        return ClassificationResult(
            intent=matched_intent,
            confidence=confidence,
            classified_at=datetime.now(timezone.utc),
        )
```

**Step 1: Write failing TDD test**

Add scoring-specific tests to `tests/unit/test_classification.py`:

```python
class TestScoringClassifier:
    """Tests for the new scoring-based classifier."""

    def setup_method(self):
        self.classifier = IntentClassifier()

    def test_scoring_overrides_priority_order(self):
        """Genuine TDD test: first-match-wins returns REFUND (priority #1);
        scoring returns COMPLAINT (more keyword hits)."""
        # Under first-match-wins: "退款" matches REFUND (priority #1) → REFUND
        # Under scoring: COMPLAINT has 投诉(2)+过期(2)+变质(2)+态度(2)+坏(2)+差(2)=12pts
        #                 REFUND has 退款(2)=2pts → COMPLAINT wins
        text = "退款！东西坏了，投诉12315，过期变质态度太差"
        result = self.classifier.classify(text)
        assert result.intent == IntentClass.COMPLAINT  # FAILS under old code

    def test_scoring_multi_intent_tie_uses_priority(self):
        """Tie on score → priority order decides (REFUND > COMPLAINT)."""
        text = "退款投诉"
        result = self.classifier.classify(text)
        assert result.intent == IntentClass.REFUND

    def test_scoring_no_keywords_other(self):
        text = "今天天气不错"
        result = self.classifier.classify(text)
        assert result.intent == IntentClass.OTHER

    def test_strong_indicator_still_fast_path(self):
        text = "我要12315投诉你们"
        result = self.classifier.classify(text)
        assert result.intent == IntentClass.COMPLAINT
        assert result.confidence == 0.9  # STRONG_INDICATOR

    def test_exclusion_penalty_reduces_score(self):
        """'退款投诉': refund excluded by '投诉' penalty. Scoring: refund=0, complaint=2."""
        text = "退款投诉"
        result = self.classifier.classify(text)
        # refund: len(退款)=2 - len(投诉 penalty)=2 = 0
        # complaint: len(投诉)=2 (no exclusion for '退款')
        # → COMPLAINT wins
        assert result.intent == IntentClass.COMPLAINT
```

**Step 2: Verify test fails under old code**
```bash
python -m pytest tests/unit/test_classification.py::TestScoringClassifier -v
```
Expected: tests `test_scoring_overrides_priority_order` and `test_exclusion_penalty_reduces_score` FAIL.

**Step 3: Implement scoring (replace lines 55-103 in classifier.py)**
See the complete replacement code above.

**Step 4: Verify test passes after scoring change**
```bash
python -m pytest tests/unit/test_classification.py::TestScoringClassifier -v
```
Expected: All 5 new tests PASS.

**Step 5: Verify existing tests still pass**
```bash
python -m pytest tests/unit/test_classification.py -v
```
Expected: All 18-20 tests pass (13 existing + 5-7 new).

**Acceptance Criteria:**
1. Strong indicators still fast-path (unchanged behavior)
2. Multi-intent text scores multiple intents correctly
3. Exclusion penalties reduce but don't block intent scores
4. No-keyword text returns OTHER
5. Existing classification tests still pass

---

### Task 2: Update existing tests

**Objective:** Fix any existing tests whose expected results change under scoring.

**Files:**
- Modify: `tests/unit/test_classification.py`

Check these test cases that might change:

1. `test_classify_return_exchange`: "我想退货，这个产品有问题" — has 退货 (2pts). But "有问题" is NOT a keyword for any rule. Should still be RETURN_EXCHANGE.

2. `test_classify_complaint`: "我要投诉你们，态度太差了" — has 投诉(2) + 态度(2) = 4pts. Exclusions for refund: 投诉 matches → -2. Currently works under first-match since COMPLAINT is after REFUND in priority. Under scoring, refund would match "退款"? No refund keyword here. So complaint wins clearly.

3. `test_classify_other`: "今天天气不错" — no keywords → OTHER.

4. `test_confidence_high_for_strong_match`: "我要申请退款，请处理" — has 申请退款(4) + 退款(2) = 6pts. Second-highest should be 0. Margin = 1.0 → HIGH.

5. `test_confidence_low_for_weak_match`: "东西坏了" — "坏了" is in COMPLAINT keywords. Score = len(坏了)=2. Second score = 0. Margin = 1.0 → HIGH. But test expects ">= 0.7". Let's check: currently "坏了" matches COMPLAINT (破损 list). Under scoring, margin=1.0, confidence = CONFIDENCE_HIGH = 0.78. Test says ">= 0.7" — PASS.

6. `TestLegalClassification` uses `IntentClassifier()` (fresh instance each test) — needs careful verification.

**Step 1: Run existing tests to get BEFORE baseline**

```bash
python -m pytest tests/unit/test_classification.py -v
```

**Expected:** All pass.

**Step 2: Run after scoring change**

```bash
python -m pytest tests/unit/test_classification.py -v
```

**Fix any failures.**

**Acceptance Criteria:**
1. All existing classification tests pass after scoring change
2. No test modifications needed that change the *intent* (confidence may change)

---

### Task 3: Run full test suite

**Objective:** Verify no regressions across the entire system.

**File:**
- Command: `python -m pytest tests/ -q --tb=short`

**Acceptance Criteria:**
1. All tests pass (or same number of pre-existing failures)
2. No evidence retrieval regressions
3. No pipeline regressions

---

### Task 4: Verify optimizer still works

**Objective:** Confirm the scoring change enables optimizer improvements.

**File:**
- Command: `python -m ticketpilot.optimizer --diagnose-only 2>&1 | grep -E '(Baseline|Found|composite)'`

**Acceptance Criteria:**
1. Optimizer still runs
2. Same number of issues found (keyword fixes should now be actionable)
3. Baseline composite is the same or better

---

## Expected outcomes

| Before (first-match-wins) | After (scoring) |
|---------------------------|-----------------|
| Rule priority matters most | Keyword density matters most |
| Adding keywords may not help (earlier rule catches) | Adding keywords always helps (raises score) |
| Exclusions = complete block | Exclusions = score penalty |
| Multi-intent text → first matching | Multi-intent text → highest scoring |
| Optimizer fixes mostly useless | Optimizer fixes become actionable |
