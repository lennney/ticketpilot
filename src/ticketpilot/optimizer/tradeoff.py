"""Trade-off analysis for keyword candidates.

For each (expected_intent, predicted_intent) confusion cluster, extract candidate
keywords via jieba, then simulate adding each one and measure:
- True Positives (TP): cases in this cluster that get fixed
- False Positives (FP): OTHER cases that now get misclassified
- Net Gain: TP - FP
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional

from ticketpilot.classification.classifier import INTENT_RULES, IntentClassifier
from ticketpilot.evaluation.schemas import EvalTicket, GoldenExpectation
from ticketpilot.optimizer.diagnostics import Diagnosis


@dataclass
class KeywordTradeoff:
    keyword: str
    target_intent: str  # which intent rule gets this keyword
    fixed_case_ids: list[str]  # confused cases now correct
    harmed_case_ids: list[str]  # correct cases now wrong
    net_gain: int  # len(fixed) - len(harmed)
    description: str

    @property
    def is_positive(self) -> bool:
        return self.net_gain > 0


@contextmanager
def _temporary_keyword(target_intent: str, keyword: str):
    """Temporarily add *keyword* to *target_intent*'s rule. Restores on exit."""
    rule = None
    for r in INTENT_RULES:
        if r.intent.value == target_intent:
            rule = r
            break
    if not rule:
        yield
        return
    original = list(rule.keywords)
    rule.keywords = original + [keyword]
    try:
        yield
    finally:
        rule.keywords = original


def _simulate_classification(text: str, target_intent: str, keyword: str) -> str:
    """Classify text AFTER adding keyword to target_intent's rule (context-manager safe)."""
    with _temporary_keyword(target_intent, keyword):
        result = IntentClassifier().classify(text)
        return result.intent.value


def _keyword_in_rule(intent_name: str, keyword: str) -> bool:
    """Check if keyword is already in the rule's keyword list."""
    for rule in INTENT_RULES:
        if rule.intent.value == intent_name:
            return keyword in rule.keywords
    return False


def analyze_keyword_tradeoff(
    diagnosis: Diagnosis,
    keyword: str,
    all_tickets: dict[str, EvalTicket],
    all_golden: dict[str, GoldenExpectation],
    current_predictions: Optional[dict[str, str]] = None,
) -> KeywordTradeoff:
    """Simulate adding *keyword* to the intent rule and measure trade-off.

    Args:
        diagnosis: The intent_mismatch diagnosis (uses expected_values for target).
        keyword: The candidate keyword to evaluate.
        all_tickets: All eval tickets by case_id.
        all_golden: All golden expectations by case_id.
        current_predictions: Optional dict of {case_id: predicted_intent} to
            avoid re-classifying outside cases (performance optimization).
    """
    target_intent = diagnosis.expected_values.get("intent", "").lower()
    if not target_intent:
        return KeywordTradeoff(
            keyword,
            target_intent,
            [],
            [],
            0,
            "No target intent from diagnosis.expected_values",
        )

    if _keyword_in_rule(target_intent, keyword):
        return KeywordTradeoff(keyword, target_intent, [], [], 0, "Already in rule")

    cluster_ids = set(diagnosis.affected_cases)
    all_ids = set(all_tickets.keys())
    outside_ids = all_ids - cluster_ids

    fixed: list[str] = []
    harmed: list[str] = []

    # Measure fix rate within the cluster
    for cid in cluster_ids:
        text = all_tickets[cid].original_text
        golden_intent = all_golden[cid].expected_issue_type
        predicted = _simulate_classification(text, target_intent, keyword)
        if predicted == golden_intent:
            fixed.append(cid)

    # Measure regression outside the cluster
    for cid in outside_ids:
        text = all_tickets[cid].original_text
        golden_intent = all_golden[cid].expected_issue_type

        # Use cached prediction if available (avoid re-classifying 300 cases)
        if current_predictions:
            original = current_predictions.get(cid, "")
        else:
            original = IntentClassifier().classify(text).intent.value

        if original == golden_intent:
            new_pred = _simulate_classification(text, target_intent, keyword)
            if new_pred != golden_intent:
                harmed.append(cid)

    return KeywordTradeoff(
        keyword=keyword,
        target_intent=target_intent,
        fixed_case_ids=fixed,
        harmed_case_ids=harmed,
        net_gain=len(fixed) - len(harmed),
        description=f"Add '{keyword}' to {target_intent}: fix {len(fixed)}, harm {len(harmed)}, net={len(fixed) - len(harmed)}",
    )
