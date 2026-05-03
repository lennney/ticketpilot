"""TicketPilot evaluation pipeline module.

Provides schemas, deterministic CSV loaders, and pure metric computation
for offline evaluation of the TicketPilot pipeline against golden expectations.

All metric functions are deterministic and operate on in-memory objects
without calling pipeline, DB, embedding provider, LLM, network, or filesystem.
"""

from ticketpilot.evaluation.schemas import (
    CaseResult,
    EvalDataset,
    EvalPrediction,
    EvalTicket,
    EvaluationMetrics,
    EvaluationSummary,
    GoldenExpectation,
    LoadResult,
    MismatchEntry,
    RiskFlagMetrics,
)
from ticketpilot.evaluation.loaders import (
    load_eval_dataset,
    load_golden_expectations,
    load_tickets_eval,
)
from ticketpilot.evaluation.metrics import (
    compute_case_metrics,
    compute_evaluation_summary,
    compute_evidence_doc_type_recall,
    compute_risk_flag_metrics,
    validate_predictions,
)

__all__ = [
    "EvalTicket",
    "GoldenExpectation",
    "EvalDataset",
    "LoadResult",
    "EvalPrediction",
    "RiskFlagMetrics",
    "EvaluationMetrics",
    "MismatchEntry",
    "CaseResult",
    "EvaluationSummary",
    "load_tickets_eval",
    "load_golden_expectations",
    "load_eval_dataset",
    "compute_risk_flag_metrics",
    "compute_evidence_doc_type_recall",
    "compute_case_metrics",
    "validate_predictions",
    "compute_evaluation_summary",
]
