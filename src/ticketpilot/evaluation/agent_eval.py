"""
Agent evaluation framework with RAGAS-style metrics.

Provides:
- Evaluation dataset management
- Faithfulness scoring
- Answer relevancy scoring
- Context precision/recall
- Version comparison
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class EvalCase:
    """Single evaluation case."""
    case_id: str
    input_text: str
    expected_intent: str
    expected_output: str | None = None
    context: list[str] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvalResult:
    """Result of evaluating a single case."""
    case_id: str
    actual_output: str
    actual_intent: str
    expected_intent: str
    intent_correct: bool
    faithfulness_score: float = 0.0
    relevancy_score: float = 0.0
    has_citations: bool = False
    duration_ms: float = 0.0
    error: str | None = None


@dataclass
class EvalReport:
    """Complete evaluation report."""
    report_id: str
    timestamp: datetime
    total_cases: int
    passed_cases: int
    failed_cases: int
    intent_accuracy: float
    avg_faithfulness: float
    avg_relevancy: float
    avg_duration_ms: float
    results: list[EvalResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        """Pass rate percentage."""
        return self.passed_cases / self.total_cases if self.total_cases > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "report_id": self.report_id,
            "timestamp": self.timestamp.isoformat(),
            "total_cases": self.total_cases,
            "passed_cases": self.passed_cases,
            "failed_cases": self.failed_cases,
            "pass_rate": round(self.pass_rate, 3),
            "intent_accuracy": round(self.intent_accuracy, 3),
            "avg_faithfulness": round(self.avg_faithfulness, 3),
            "avg_relevancy": round(self.avg_relevancy, 3),
            "avg_duration_ms": round(self.avg_duration_ms, 2),
            "results": [
                {
                    "case_id": r.case_id,
                    "intent_correct": r.intent_correct,
                    "faithfulness": round(r.faithfulness_score, 3),
                    "relevancy": round(r.relevancy_score, 3),
                    "has_citations": r.has_citations,
                    "duration_ms": round(r.duration_ms, 2),
                    "error": r.error,
                }
                for r in self.results
            ],
            "metadata": self.metadata,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def save(self, directory: str | Path = "reports/eval") -> Path:
        """Save report to file."""
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        
        file_path = dir_path / f"eval_{self.report_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        file_path.write_text(self.to_json(), encoding="utf-8")
        return file_path


class EvalDataset:
    """Evaluation dataset manager."""
    
    def __init__(self, cases: list[EvalCase] | None = None):
        self.cases = cases or []
    
    def add_case(self, case: EvalCase) -> None:
        """Add a case to the dataset."""
        self.cases.append(case)
    
    def load(self, path: str | Path) -> None:
        """Load cases from JSON file."""
        with open(path) as f:
            data = json.load(f)
        
        for item in data:
            self.cases.append(EvalCase(
                case_id=item.get("case_id", str(uuid.uuid4())),
                input_text=item["input_text"],
                expected_intent=item["expected_intent"],
                expected_output=item.get("expected_output"),
                context=item.get("context"),
                metadata=item.get("metadata", {}),
            ))
    
    def save(self, path: str | Path) -> None:
        """Save cases to JSON file."""
        data = [
            {
                "case_id": c.case_id,
                "input_text": c.input_text,
                "expected_intent": c.expected_intent,
                "expected_output": c.expected_output,
                "context": c.context,
                "metadata": c.metadata,
            }
            for c in self.cases
        ]
        
        with open(path, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def compute_faithfulness(
    actual_output: str,
    context: list[str],
    scorer_type: str = "keyword",
) -> float:
    """
    Compute faithfulness score.

    Checks if the actual output is grounded in the context.

    Args:
        actual_output: The generated answer text
        context: List of context passages used to generate the answer
        scorer_type: "keyword" (default, backward compatible) or "nli"

    Returns: 0.0 to 1.0
    """
    if scorer_type == "nli":
        from ticketpilot.evaluation.nli_scorer import NLIScorer

        return NLIScorer().score_faithfulness(actual_output, context)

    # Keyword overlap (original behavior)
    if not context or not actual_output:
        return 0.5  # Default score when no context

    all_context = " ".join(context)

    output_words = set(actual_output.replace("。", " ").replace("，", " ").replace("、", " ").split())
    context_words = set(all_context.replace("。", " ").replace("，", " ").replace("、", " ").split())

    if not output_words:
        return 0.5

    overlap = output_words & context_words
    score = len(overlap) / len(output_words) if output_words else 0

    return 0.5 + (score * 0.5)


def compute_relevancy(
    input_text: str,
    actual_output: str,
    scorer_type: str = "keyword",
) -> float:
    """
    Compute answer relevancy score.

    Checks if the output addresses the input question.

    Args:
        input_text: The original question/ticket text
        actual_output: The generated answer text
        scorer_type: "keyword" (default, backward compatible) or "nli"

    Returns: 0.0 to 1.0
    """
    if scorer_type == "nli":
        from ticketpilot.evaluation.nli_scorer import NLIScorer

        return NLIScorer().score_relevancy(input_text, actual_output)

    # Keyword overlap (original behavior)
    if not input_text or not actual_output:
        return 0.5  # Default score

    input_clean = input_text.replace("？", "").replace("。", "").replace("，", " ").replace("、", " ")
    output_clean = actual_output.replace("？", "").replace("。", "").replace("，", " ").replace("、", " ")

    input_words = set(input_clean.split())
    output_words = set(output_clean.split())

    if not input_words:
        return 0.5

    overlap = input_words & output_words
    score = len(overlap) / len(input_words)

    return 0.5 + (score * 0.5)


def run_evaluation(
    dataset: EvalDataset,
    agent_fn,
    pass_threshold: float = 0.7,
    scorer_type: str = "keyword",
) -> EvalReport:
    """
    Run evaluation on a dataset.
    
    Args:
        dataset: Evaluation dataset
        agent_fn: Function that takes input_text and returns (output, intent)
        pass_threshold: Threshold for passing a case
    
    Returns:
        EvalReport with results
    """
    results = []
    passed = 0
    failed = 0
    
    for case in dataset.cases:
        try:
            # Run agent
            import time
            start = time.time()
            output, intent = agent_fn(case.input_text)
            duration = (time.time() - start) * 1000
            
            # Check intent
            intent_correct = intent == case.expected_intent
            
            # Compute scores
            faithfulness = compute_faithfulness(output, case.context or [], scorer_type=scorer_type)
            relevancy = compute_relevancy(case.input_text, output, scorer_type=scorer_type)
            has_citations = "[" in output and "]" in output
            
            # Determine pass/fail
            score = (faithfulness + relevancy) / 2
            if score >= pass_threshold:
                passed += 1
            else:
                failed += 1
            
            results.append(EvalResult(
                case_id=case.case_id,
                actual_output=output,
                actual_intent=intent,
                expected_intent=case.expected_intent,
                intent_correct=intent_correct,
                faithfulness_score=faithfulness,
                relevancy_score=relevancy,
                has_citations=has_citations,
                duration_ms=duration,
            ))
        except Exception as e:
            failed += 1
            results.append(EvalResult(
                case_id=case.case_id,
                actual_output="",
                actual_intent="",
                expected_intent=case.expected_intent,
                intent_correct=False,
                error=str(e),
            ))
    
    # Compute averages
    total = len(results)
    intent_correct = sum(1 for r in results if r.intent_correct)
    avg_faithfulness = sum(r.faithfulness_score for r in results) / total if total > 0 else 0
    avg_relevancy = sum(r.relevancy_score for r in results) / total if total > 0 else 0
    avg_duration = sum(r.duration_ms for r in results) / total if total > 0 else 0
    
    return EvalReport(
        report_id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        total_cases=total,
        passed_cases=passed,
        failed_cases=failed,
        intent_accuracy=intent_correct / total if total > 0 else 0,
        avg_faithfulness=avg_faithfulness,
        avg_relevancy=avg_relevancy,
        avg_duration_ms=avg_duration,
        results=results,
    )
