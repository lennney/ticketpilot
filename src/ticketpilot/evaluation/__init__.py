"""TicketPilot evaluation pipeline module.

Provides schemas and deterministic CSV loaders for offline evaluation
of the TicketPilot pipeline against golden expectations.
"""

from ticketpilot.evaluation.schemas import (
    EvalDataset,
    EvalTicket,
    GoldenExpectation,
    LoadResult,
)
from ticketpilot.evaluation.loaders import (
    load_golden_expectations,
    load_tickets_eval,
    load_eval_dataset,
)

__all__ = [
    "EvalTicket",
    "GoldenExpectation",
    "EvalDataset",
    "LoadResult",
    "load_tickets_eval",
    "load_golden_expectations",
    "load_eval_dataset",
]
