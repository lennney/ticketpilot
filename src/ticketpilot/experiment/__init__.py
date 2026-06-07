"""A/B Experiment Framework for TicketPilot.

Run the same tickets through two configurations and compare metrics.
Deterministic — no LLM calls.
"""

from ticketpilot.experiment.config import ExperimentConfig
from ticketpilot.experiment.reporter import ExperimentReport
from ticketpilot.experiment.runner import ExperimentRunner

__all__ = ["ExperimentConfig", "ExperimentRunner", "ExperimentReport"]
