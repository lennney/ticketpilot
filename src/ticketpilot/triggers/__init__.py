"""Trigger mechanisms for TicketPilot pipeline.

Supports:
- CLI trigger: python -m ticketpilot.triggers.cli
- Webhook trigger: python -m ticketpilot.triggers.webhook
"""

from ticketpilot.triggers.cli import main as cli_main
from ticketpilot.triggers.webhook import main as webhook_main

__all__ = ["cli_main", "webhook_main"]
