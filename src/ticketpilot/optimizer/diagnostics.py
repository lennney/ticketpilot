"""Diagnostics — analyzes evaluation results to find failing patterns.

Examines EvaluationSummary per-case results, groups mismatches into
actionable Diagnosis objects, and ranks them by estimated composite
score gain so the optimizer knows which fixes to attempt first.
"""

from __future__ import annotations

import jieba
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Any

from ticketpilot.evaluation.schemas import (
    CaseResult,
    EvaluationSummary,
)

# 意图优先级顺序（first-match-wins）
PRIORITY_ORDER = [
    "REFUND",
    "RETURN_EXCHANGE",
    "ACCOUNT_ISSUE",
    "TECHNICAL_ISSUE",
    "PRODUCT_CONSULTING",
    "LOGISTICS",
    "COMPLAINT",
    "OTHER",
]


# ---------------------------------------------------------------------------
# Diagnosis dataclass
# ---------------------------------------------------------------------------


@dataclass
class Diagnosis:
    """A single diagnosable pattern with suggested fix and estimated gain."""

    type: str  # one of the diagnosis type constants below
    priority: int  # from FIX_PRIORITY
    affected_cases: list[str]  # case IDs exhibiting this pattern
    expected_values: dict  # what golden expects
    predicted_values: dict  # what system predicted
    suggested_fix_type: str  # fix type key from FIX_PRIORITY
    suggested_keywords: list[str]  # for keyword-based fixes
    fix_gain: float  # estimated composite score gain
    description: str  # human-readable
    details: dict[str, Any] = field(default_factory=dict)  # per-mismatch data


# Diagnosis type constants
TYPE_INTENT_MISMATCH = "intent_mismatch"
TYPE_RISK_MISS = "risk_miss"
TYPE_RISK_FALSE_POSITIVE = "risk_false_positive"
TYPE_SEVERITY_WRONG = "severity_wrong"
TYPE_EVIDENCE_GAP = "evidence_gap"
TYPE_CONFIDENCE_MISROUTE = "confidence_misroute"

# Meta-flags that are set programmatically by the pipeline, not by keyword
# matching. The optimizer should NOT suggest keyword-based fixes for these.
_META_RISK_FLAGS: set[str] = {"INSUFFICIENT_EVIDENCE", "LOW_CONFIDENCE"}


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------


def _compute_fix_gain(
    affected_cases: int,
    metric_weight: float,
    total_cases: int,
) -> float:
    """Compute estimated composite score gain from fixing a pattern.

    Gain = (cases_affected / total_cases) * metric_weight.
    Returns 0.0 if total_cases is 0.
    """
    if total_cases <= 0:
        return 0.0
    return (affected_cases / total_cases) * metric_weight


def _get_existing_intent_keywords(intent_name: str) -> list[str]:
    """Get existing Chinese keywords for an intent from classification/rules.py.

    Parses the source file to extract keywords for the given intent.
    Falls back to empty list if parsing fails.
    """
    from pathlib import Path

    rules_path = Path(__file__).parent.parent.parent / "classification" / "rules.py"
    if not rules_path.is_file():
        return []

    try:
        source = rules_path.read_text(encoding="utf-8")
        # Find the IntentRule block for the target intent
        intent_pattern = rf"intent=IntentClass\.{intent_name}\b"
        intent_match = re.search(intent_pattern, source)
        if not intent_match:
            return []

        # Find keywords=[...] after intent match
        search_start = intent_match.start()
        kw_match = re.search(r"keywords=\[(.*?)\]", source[search_start:], re.DOTALL)
        if not kw_match:
            return []

        kw_body = kw_match.group(1).strip()
        if not kw_body:
            return []
        return [m.group(1) for m in re.finditer(r'"([^"]+)"', kw_body)]
    except Exception:  # noqa: BLE001
        return []


def _get_existing_risk_keywords(flag_name: str) -> list[str]:
    """Get existing Chinese keywords for a risk flag from risk/rules.py.

    Parses the source file to extract keywords for the given flag.
    Falls back to empty list if parsing fails.
    """
    from pathlib import Path

    rules_path = Path(__file__).parent.parent.parent / "risk" / "rules.py"
    if not rules_path.is_file():
        return []

    try:
        source = rules_path.read_text(encoding="utf-8")
        # Find the RiskRule block for the target flag
        flag_pattern = rf"flag=RiskFlag\.{flag_name}\b"
        flag_match = re.search(flag_pattern, source)
        if not flag_match:
            return []

        # Find keywords=[...] after flag match
        search_start = flag_match.start()
        kw_match = re.search(r"keywords=\[(.*?)\]", source[search_start:], re.DOTALL)
        if not kw_match:
            return []

        kw_body = kw_match.group(1).strip()
        if not kw_body:
            return []
        return [m.group(1) for m in re.finditer(r'"([^"]+)"', kw_body)]
    except Exception:  # noqa: BLE001
        return []


# Common Chinese stop words to filter out from keyword extraction
_CHINESE_STOP_WORDS: set[str] = {
    # 基础停用词
    "的",
    "了",
    "是",
    "在",
    "我",
    "有",
    "和",
    "就",
    "不",
    "人",
    "都",
    "一",
    "一个",
    "上",
    "也",
    "很",
    "到",
    "说",
    "要",
    "去",
    "你",
    "会",
    "着",
    "没有",
    "看",
    "好",
    "自己",
    "这",
    "他",
    "她",
    "它",
    "们",
    "那",
    "被",
    "把",
    "让",
    "用",
    "来",
    "过",
    "对",
    "能",
    "可",
    "但",
    "而",
    "又",
    "如果",
    "因为",
    "所以",
    "虽然",
    "还是",
    "已经",
    "什么",
    "怎么",
    "这个",
    "那个",
    "一下",
    "可以",
    "没",
    "做",
    "给",
    "还",
    "想",
    "知道",
    "觉得",
    "应该",
    "时候",
    "现在",
    "比较",
    "真的",
    "其实",
    "问题",
    "情况",
    "东西",
    "地方",
    # 高频通用词（出现在大多数工单中，无区分度）
    "你们",
    "我们",
    "他们",
    "订单",
    "单号",
    "订单号",
    "申请",
    "处理",
    "问题",
    "咨询",
    "需要",
    "请问",
    "客服",
    "平台",
    "收到",
    "商品",
    "产品",
    "购买",
    "买",
    "货",
    "件",
    # Additional stopwords from the task spec
    "吗",
    "吧",
    "啊",
    "呢",
    "太",
    "与",
    "或",
    "卖",
    "两",
    "三",
    "天",
    "钱",
    "时",
    "间",
    "再",
    "才",
    "所",
    "为",
    "于",
    "以",
    "为什么",
    "不是",
    "就是",
    "不要",
    "这么",
    "那么",
    "只",
}


def _extract_chinese_keywords(
    texts: list[str],
    existing_keywords: list[str],
    max_keywords: int = 5,
) -> list[str]:
    """Extract frequent Chinese keywords from ticket texts.

    Uses jieba word segmentation to tokenize Chinese text into proper
    words, then ranks by document frequency. Much more accurate than
    character-based n-grams which produce meaningless fragments.

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
            word = word.strip()
            # Skip: single characters, stop words, existing keywords, non-Chinese tokens
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

    # Filter out words that appear in >75% of texts (too generic)
    threshold = len(texts) * 0.75
    filtered = [(w, c) for w, c in word_counter.most_common() if c <= threshold]

    # Return top keywords by frequency
    return [word for word, _ in filtered[:max_keywords]]


def _analyze_causal_features(
    misclassified_texts: list[str],
    correctly_classified_texts: list[str],
    existing_keywords: list[str],
    max_features: int = 3,
) -> list[str]:
    """Find distinguishing features in misclassified vs correctly classified texts.

    Analyzes n-grams (2-4 chars) that appear significantly more often
    in the misclassified set than in the correctly classified set.

    Args:
        misclassified_texts: Texts that were misclassified.
        correctly_classified_texts: Texts of the same intent that were correctly
            classified.
        existing_keywords: Keywords already in the rule (to exclude).
        max_features: Max distinguishing features to return.

    Returns:
        List of distinguishing feature keywords, sorted by lift score.
    """
    from collections import Counter

    if not misclassified_texts:
        return []
    if not correctly_classified_texts:
        # No reference — fall back to common keywords in misclassified texts
        fallback_kws = _extract_chinese_keywords(
            misclassified_texts, existing_keywords, max_keywords=max_features
        )
        # Filter out terms that already appear in high-priority rules
        return [kw for kw in fallback_kws if kw not in existing_keywords][:max_features]

    existing_set = set(existing_keywords)

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

    mis_counter = _jieba_words(misclassified_texts)
    correct_counter = _jieba_words(correctly_classified_texts)
    n_mis = len(misclassified_texts)
    n_correct = len(correctly_classified_texts) or 1  # avoid division by zero

    # Compute lift: (freq_in_mis / n_mis) / (freq_in_correct / n_correct)
    scored: list[tuple[float, str]] = []
    for gram, freq in mis_counter.most_common(50):
        correct_freq = correct_counter.get(gram, 0)
        # Laplace smoothing (α=0.1) to avoid division by zero / infinite lift
        lift = (freq / n_mis) / ((correct_freq + 0.1) / n_correct)
        if lift >= 1.5 and gram not in existing_set:
            scored.append((lift, gram))

    scored.sort(key=lambda x: -x[0])
    return [gram for _, gram in scored[:max_features]]


def _enrich_with_keyword_candidates(
    diagnosis: Diagnosis,
    tickets: dict[str, Any],
) -> Diagnosis:
    """Add jieba keyword candidates from the affected cases' text.

    Uses _extract_chinese_keywords() to extract keywords, filtering out
    single-character tokens, already-existing keywords for this intent,
    and common stopwords. Stores up to 5 candidates in
    diagnosis.details["keyword_candidates"].

    Args:
        diagnosis: An intent_mismatch Diagnosis object.
        tickets: Dict mapping case_id to EvalTicket objects.

    Returns:
        The same Diagnosis with keyword_candidates populated in details.
    """
    expected_intent = str(diagnosis.expected_values.get("intent", "")).upper()
    existing_kws = (
        _get_existing_intent_keywords(expected_intent) if expected_intent else []
    )

    texts = []
    for cid in diagnosis.affected_cases:
        ticket = tickets.get(cid)
        if ticket and hasattr(ticket, "original_text"):
            texts.append(ticket.original_text)

    candidates = _extract_chinese_keywords(texts, existing_kws, max_keywords=5)
    if candidates:
        diagnosis.details["keyword_candidates"] = candidates
    return diagnosis


def _build_confusion_matrix(
    results: dict[str, CaseResult],
) -> dict[tuple[str, str], list[str]]:
    """Build an intent confusion matrix from case results.

    Returns dict mapping (expected, predicted) → list of case_ids.
    Only includes mismatches (expected != predicted).
    """
    matrix: dict[tuple[str, str], list[str]] = {}
    for case_id, case in results.items():
        if not case.metrics.intent_accuracy:
            expected = case.golden.expected_issue_type
            predicted = case.prediction.predicted_issue_type
            key = (expected, predicted)
            matrix.setdefault(key, []).append(case_id)
    return matrix


def _analyze_risk_flags(
    results: dict[str, CaseResult],
    total_cases: int,
    weight: float,
    dataset: dict | None = None,
) -> list[Diagnosis]:
    """Analyze risk flag mismatches and produce diagnoses.

    Separates missed flags (false negatives) from false positives.

    Args:
        dataset: Optional dict of case_id → EvalTicket for extracting
        original_text to find Chinese keywords.
    """
    diagnoses: list[Diagnosis] = []
    risk_miss_cases: list[str] = []
    risk_fp_cases: list[str] = []

    # Track per-flag statistics
    missed_flag_counts: Counter[str] = Counter()
    fp_flag_counts: Counter[str] = Counter()

    for case_id, case in results.items():
        if case.metrics.risk_flag_metrics.exact_match:
            continue
        golden_flags = set(case.golden.expected_risk_flags)
        predicted_flags = set(case.prediction.predicted_risk_flags)

        # Missed flags (expected but not predicted)
        missed = golden_flags - predicted_flags
        if missed:
            risk_miss_cases.append(case_id)
            for flag in missed:
                missed_flag_counts[flag] += 1

        # False positives (predicted but not expected)
        false_positives = predicted_flags - golden_flags
        if false_positives:
            risk_fp_cases.append(case_id)
            for flag in false_positives:
                fp_flag_counts[flag] += 1

    # Generate one diagnosis per missed risk flag (fixer expects single risk_flag)
    for flag_name, count in missed_flag_counts.most_common(3):
        flag_str = (
            str(flag_name.value) if hasattr(flag_name, "value") else str(flag_name)
        )
        # Skip meta-flags that are set programmatically, not by keyword matching
        if flag_str.upper() in _META_RISK_FLAGS:
            continue
        affected = [
            cid
            for cid in risk_miss_cases
            if cid in results and flag_name in results[cid].golden.expected_risk_flags
        ]
        gain = _compute_fix_gain(len(affected), weight, total_cases)

        # Extract Chinese keywords from ticket texts of affected cases
        suggested_keywords = [flag_str]  # fallback to English enum name
        if dataset:
            texts = []
            for cid in affected:
                ticket = dataset.get(cid)
                if ticket and hasattr(ticket, "original_text"):
                    texts.append(ticket.original_text)
            if texts:
                # Get existing keywords for this risk flag (from risk/rules.py)
                existing_kws = _get_existing_risk_keywords(flag_str)
                extracted = _extract_chinese_keywords(texts, existing_kws)
                if extracted:
                    suggested_keywords = extracted

        diagnoses.append(
            Diagnosis(
                type=TYPE_RISK_MISS,
                priority=2,
                affected_cases=affected,
                expected_values={"risk_flag": flag_str.upper()},
                predicted_values={},
                suggested_fix_type="risk_keyword",
                suggested_keywords=suggested_keywords,
                fix_gain=gain,
                description=(f"Risk flag '{flag_str}' missed in {len(affected)} cases"),
            )
        )

    # Generate risk_false_positive diagnosis (skip — removing keywords is risky)

    return diagnoses


def _analyze_evidence(
    results: dict[str, CaseResult],
    total_cases: int,
    weight: float,
) -> list[Diagnosis]:
    """Analyze evidence doc type recall gaps."""
    diagnoses: list[Diagnosis] = []
    evidence_gap_cases: list[str] = []
    missing_doc_counts: Counter[str] = Counter()

    for case_id, case in results.items():
        if case.metrics.evidence_doc_type_recall >= 1.0:
            continue
        evidence_gap_cases.append(case_id)
        golden_docs = set(case.golden.expected_evidence_doc_types)
        predicted_docs = set(case.prediction.predicted_evidence_doc_types)
        missing = golden_docs - predicted_docs
        for doc_type in missing:
            missing_doc_counts[doc_type] += 1

    # Evidence gaps — no supported fix type yet (reranker_weight not implemented)
    # Skip to avoid wasting rounds on unfixable diagnoses

    return diagnoses


def _analyze_severity(
    results: dict[str, CaseResult],
    total_cases: int,
    weight: float,
) -> list[Diagnosis]:
    """Analyze severity mismatches."""
    diagnoses: list[Diagnosis] = []
    severity_cases: list[str] = []
    severity_confusion: Counter[tuple[str, str]] = Counter()

    for case_id, case in results.items():
        if case.metrics.severity_accuracy:
            continue
        severity_cases.append(case_id)
        expected = case.golden.expected_severity
        predicted = case.prediction.predicted_severity
        severity_confusion[(expected, predicted)] += 1

    # Severity mismatches — severity is derived from risk flag counts in assessor.py
    # No direct fix available; fixing risk flags often improves severity as side effect
    # Skip to avoid wasting rounds

    return diagnoses


def _analyze_confidence_misroute(
    results: dict[str, CaseResult],
    total_cases: int,
    weight: float,
) -> list[Diagnosis]:
    """Analyze must_human_review / no_auto_send misroutes.

    Generates a single diagnosis suggesting threshold adjustment when
    confidence misroutes are detected. The fixer's ``_fix_confidence_threshold``
    handler adjusts ``CONFIDENCE_MEDIUM`` as a safe starting point.
    """
    diagnoses: list[Diagnosis] = []
    misroute_cases: list[str] = []

    for case_id, case in results.items():
        human_review_correct = case.metrics.must_human_review_accuracy
        auto_send_correct = case.metrics.no_auto_send_compliance
        if not human_review_correct or not auto_send_correct:
            misroute_cases.append(case_id)

    if not misroute_cases:
        return diagnoses

    # Import current config values to suggest a meaningful adjustment
    try:
        from ticketpilot.config import CONFIDENCE_MEDIUM

        adjusted = round(CONFIDENCE_MEDIUM * 0.85, 2)  # suggest 15% lower
    except ImportError:
        adjusted = 0.5  # fallback

    gain = _compute_fix_gain(len(misroute_cases), weight, total_cases)
    diagnoses.append(
        Diagnosis(
            type=TYPE_CONFIDENCE_MISROUTE,
            priority=1,  # confidence_threshold is L1 (safest fix)
            affected_cases=misroute_cases,
            expected_values={
                "threshold_name": "CONFIDENCE_MEDIUM",
                "new_value": adjusted,
            },
            predicted_values={},
            suggested_fix_type="confidence_threshold",
            suggested_keywords=[],
            fix_gain=gain,
            description=(
                f"Confidence threshold misroute in {len(misroute_cases)} cases "
                f"(must_human_review or no_auto_send incorrect)"
            ),
        )
    )

    return diagnoses


# ---------------------------------------------------------------------------
# Main diagnostics engine
# ---------------------------------------------------------------------------


class DiagnosticsEngine:
    """Analyze evaluation results and produce ranked diagnoses."""

    def __init__(self, weights: dict[str, float]):
        """Initialize with composite score weights.

        Args:
            weights: Dict mapping metric names to weights (e.g. from COMPOSITE_WEIGHTS).
        """
        self.weights = weights

    def analyze(
        self,
        summary: EvaluationSummary,
        dataset: dict,
    ) -> list[Diagnosis]:
        """Analyze evaluation summary, return diagnoses sorted by fix_gain descending.

        Args:
            summary: The full evaluation summary with per-case results.
            dataset: The raw dataset (tickets + golden), keyed by case_id.

        Returns:
            List of Diagnosis objects, sorted by fix_gain descending.
        """
        results = summary.results
        total_cases = summary.total_cases

        # Weight lookup helpers — use the weight for the relevant metric
        intent_weight = self.weights.get("intent", 0.25)
        risk_weight = self.weights.get("risk_f1", 0.20)
        evidence_weight = self.weights.get("evidence", 0.15)
        severity_weight = self.weights.get("severity", 0.20)
        # Confidence misroute touches no_auto_send + must_human_review
        confidence_weight = self.weights.get("no_auto_send", 0.10) + self.weights.get(
            "fallback", 0.10
        )

        all_diagnoses: list[Diagnosis] = []

        # 1. Intent mismatches — build confusion matrix
        confusion = _build_confusion_matrix(results)
        for (expected, predicted), case_ids in confusion.items():
            gain = _compute_fix_gain(len(case_ids), intent_weight, total_cases)
            confusion_details = [
                {
                    "case_id": cid,
                    "expected": results[cid].golden.expected_issue_type,
                    "predicted": results[cid].prediction.predicted_issue_type,
                }
                for cid in case_ids
                if cid in results
            ]

            # Extract Chinese keywords from ticket texts of mismatched cases
            suggested_keywords = [expected]  # fallback to English enum name
            if dataset:
                mis_texts = []
                for cid in case_ids:
                    ticket = dataset.get(cid)
                    if ticket and hasattr(ticket, "original_text"):
                        mis_texts.append(ticket.original_text)

                # 决定使用哪种修复策略
                fix_type = "intent_keyword"

                # 如果 predicted intent 的优先级高于 expected intent
                # 说明是 first-match-wins 问题，应该用 exclusion_rule
                if (
                    expected.upper() in PRIORITY_ORDER
                    and predicted.upper() in PRIORITY_ORDER
                ):
                    expected_prio = PRIORITY_ORDER.index(expected.upper())
                    predicted_prio = PRIORITY_ORDER.index(predicted.upper())
                    if predicted_prio < expected_prio:
                        fix_type = "exclusion_rule"

                if mis_texts:
                    if fix_type == "exclusion_rule":
                        # 对于 exclusion_rule 修复：找误分类工单中
                        # 能区分「这是 X 不是 Y」的特征词
                        # 参考文本：找到正确分类为 predicted intent 的工单
                        correct_texts = []
                        for cid, cr in results.items():
                            if cr.prediction.predicted_issue_type == predicted:
                                if cr.metrics.intent_accuracy:
                                    ticket = dataset.get(cid)
                                    if ticket and hasattr(ticket, "original_text"):
                                        correct_texts.append(ticket.original_text)

                        # 获取 predicted intent 已有的关键词（作为排除项）
                        existing_kws = _get_existing_intent_keywords(predicted.upper())

                        # 因果分析：找误分类工单中有、但正确分类工单中没有的特征词
                        causal = _analyze_causal_features(
                            mis_texts,
                            correct_texts,
                            existing_keywords=existing_kws,
                            max_features=3,
                        )
                        if causal:
                            suggested_keywords = causal
                    else:
                        # intent_keyword 修复：原有策略不变
                        existing_kws = _get_existing_intent_keywords(expected.upper())
                        extracted = _extract_chinese_keywords(mis_texts, existing_kws)
                        if extracted:
                            suggested_keywords = extracted

            all_diagnoses.append(
                Diagnosis(
                    type=TYPE_INTENT_MISMATCH,
                    priority=2,  # intent_keyword priority
                    affected_cases=case_ids,
                    expected_values={"intent": expected.upper()},
                    predicted_values={"predicted_intent": predicted},
                    suggested_fix_type=fix_type,
                    suggested_keywords=suggested_keywords,
                    fix_gain=gain,
                    description=(
                        f"Intent mismatch: expected '{expected}', predicted '{predicted}' "
                        f"({len(case_ids)} cases)"
                    ),
                    details={"confusions": confusion_details},
                )
            )

        # Enrich intent_mismatch diagnoses with jieba keyword candidates
        for i, diag in enumerate(all_diagnoses):
            if diag.type == TYPE_INTENT_MISMATCH:
                all_diagnoses[i] = _enrich_with_keyword_candidates(diag, dataset)

        # 2. Risk flag analysis
        all_diagnoses.extend(
            _analyze_risk_flags(results, total_cases, risk_weight, dataset)
        )

        # 3. Evidence doc type recall
        all_diagnoses.extend(_analyze_evidence(results, total_cases, evidence_weight))

        # 4. Severity mismatches
        all_diagnoses.extend(_analyze_severity(results, total_cases, severity_weight))

        # 5. Confidence misroute
        all_diagnoses.extend(
            _analyze_confidence_misroute(results, total_cases, confidence_weight)
        )

        # Sort by fix_gain descending
        all_diagnoses.sort(key=lambda d: d.fix_gain, reverse=True)
        return all_diagnoses
