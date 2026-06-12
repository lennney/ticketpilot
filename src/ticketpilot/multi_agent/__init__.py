"""Multi-Agent Orchestrator for TicketPilot.

Routes tickets to specialized agents based on intent:
- RefundAgent: Handles refund-related tickets
- ComplaintAgent: Handles complaints and escalations
- LogisticsAgent: Handles shipping and delivery issues
- TechnicalAgent: Handles technical issues
- DefaultAgent: Handles other intents

Re-exports key classes for cleaner imports:
    from ticketpilot.multi_agent import BaseAgent, Orchestrator
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from ticketpilot.drafting.draft_agent import DraftAgent
from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.schema.evidence import EvidenceCandidate

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for specialized agents."""

    def __init__(self, name: str, template_id: str = "default"):
        self.name = name
        self.template_id = template_id
        self._draft_agent = DraftAgent(template_id=template_id)
    
    @abstractmethod
    def generate_draft(
        self,
        normalized_text: str,
        issue_type: str,
        risk_flags: list[str],
        severity: str,
        must_human_review: bool,
        evidence_candidates: list[EvidenceCandidate],
    ) -> DraftReply:
        """Generate a draft reply for the ticket."""
        pass


class RefundAgent(BaseAgent):
    """Specialized agent for refund-related tickets."""

    def __init__(self):
        super().__init__("RefundAgent", template_id="refund")
    
    def generate_draft(
        self,
        normalized_text: str,
        issue_type: str,
        risk_flags: list[str],
        severity: str,
        must_human_review: bool,
        evidence_candidates: list[EvidenceCandidate],
    ) -> DraftReply:
        """Generate refund-focused reply."""
        return self._draft_agent.generate_draft(
            normalized_text=normalized_text,
            issue_type=issue_type,
            risk_flags=risk_flags,
            severity=severity,
            must_human_review=must_human_review,
            evidence_candidates=evidence_candidates,
        )


class ComplaintAgent(BaseAgent):
    """Specialized agent for complaints and escalations."""

    def __init__(self):
        super().__init__("ComplaintAgent", template_id="complaint")
    
    def generate_draft(
        self,
        normalized_text: str,
        issue_type: str,
        risk_flags: list[str],
        severity: str,
        must_human_review: bool,
        evidence_candidates: list[EvidenceCandidate],
    ) -> DraftReply:
        """Generate complaint-focused reply."""
        # Complaints always need human review
        must_human_review = True
        
        return self._draft_agent.generate_draft(
            normalized_text=normalized_text,
            issue_type=issue_type,
            risk_flags=risk_flags,
            severity=severity,
            must_human_review=must_human_review,
            evidence_candidates=evidence_candidates,
        )


class LogisticsAgent(BaseAgent):
    """Specialized agent for logistics issues."""

    def __init__(self):
        super().__init__("LogisticsAgent", template_id="logistics")
    
    def generate_draft(
        self,
        normalized_text: str,
        issue_type: str,
        risk_flags: list[str],
        severity: str,
        must_human_review: bool,
        evidence_candidates: list[EvidenceCandidate],
    ) -> DraftReply:
        """Generate logistics-focused reply."""
        return self._draft_agent.generate_draft(
            normalized_text=normalized_text,
            issue_type=issue_type,
            risk_flags=risk_flags,
            severity=severity,
            must_human_review=must_human_review,
            evidence_candidates=evidence_candidates,
        )


class TechnicalAgent(BaseAgent):
    """Specialized agent for technical issues."""

    def __init__(self):
        super().__init__("TechnicalAgent", template_id="technical")
    
    def generate_draft(
        self,
        normalized_text: str,
        issue_type: str,
        risk_flags: list[str],
        severity: str,
        must_human_review: bool,
        evidence_candidates: list[EvidenceCandidate],
    ) -> DraftReply:
        """Generate technical-focused reply."""
        return self._draft_agent.generate_draft(
            normalized_text=normalized_text,
            issue_type=issue_type,
            risk_flags=risk_flags,
            severity=severity,
            must_human_review=must_human_review,
            evidence_candidates=evidence_candidates,
        )


class DefaultAgent(BaseAgent):
    """Default agent for other intents."""

    def __init__(self):
        super().__init__("DefaultAgent", template_id="default")
    
    def generate_draft(
        self,
        normalized_text: str,
        issue_type: str,
        risk_flags: list[str],
        severity: str,
        must_human_review: bool,
        evidence_candidates: list[EvidenceCandidate],
    ) -> DraftReply:
        """Generate default reply."""
        return self._draft_agent.generate_draft(
            normalized_text=normalized_text,
            issue_type=issue_type,
            risk_flags=risk_flags,
            severity=severity,
            must_human_review=must_human_review,
            evidence_candidates=evidence_candidates,
        )


# Alias for facade
BaseSpecialist = BaseAgent
BillingSpecialist = RefundAgent
GeneralSpecialist = DefaultAgent


class Orchestrator:
    """
    Multi-Agent Orchestrator.
    
    Routes tickets to specialized agents based on intent.
    """
    
    def __init__(self):
        # Initialize specialized agents
        self._agents = {
            "refund": RefundAgent(),
            "return_exchange": LogisticsAgent(),  # Returns are logistics (wrong/damaged items)
            "complaint": ComplaintAgent(),
            "logistics": LogisticsAgent(),
            "technical_issue": TechnicalAgent(),
            "account_issue": TechnicalAgent(),  # Same agent for account issues
            "product_consulting": DefaultAgent(),
            "other": DefaultAgent(),
        }
        
        # Default agent
        self._default_agent = DefaultAgent()
    
    def get_agent(self, intent: str) -> BaseAgent:
        """Get the appropriate agent for the intent."""
        return self._agents.get(intent, self._default_agent)
    
    def generate_draft(
        self,
        normalized_text: str,
        issue_type: str,
        risk_flags: list[str],
        severity: str,
        must_human_review: bool,
        evidence_candidates: list[EvidenceCandidate],
    ) -> DraftReply:
        """
        Generate a draft reply using the appropriate specialized agent.

        Legal risk tickets are always routed to ComplaintAgent regardless
        of intent classification.
        """
        # Legal risk overrides intent-based routing
        if "legal_risk" in risk_flags:
            agent = ComplaintAgent()
            logger.info(
                "Orchestrator: legal_risk detected, routing to ComplaintAgent",
            )
        else:
            agent = self.get_agent(issue_type)
            logger.info(
                "Orchestrator: routing to %s for intent=%s",
                agent.name,
                issue_type,
            )

        return agent.generate_draft(
            normalized_text=normalized_text,
            issue_type=issue_type,
            risk_flags=risk_flags,
            severity=severity,
            must_human_review=must_human_review,
            evidence_candidates=evidence_candidates,
        )


# Global orchestrator instance
_orchestrator: Orchestrator | None = None


def get_orchestrator() -> Orchestrator:
    """Get or create the global orchestrator."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator


def generate_draft_with_orchestrator(
    normalized_text: str,
    issue_type: str,
    risk_flags: list[str],
    severity: str,
    must_human_review: bool,
    evidence_candidates: list[EvidenceCandidate],
) -> DraftReply:
    """
    Generate a draft reply using the multi-agent orchestrator.
    
    This is the main entry point for the multi-agent system.
    """
    orchestrator = get_orchestrator()
    return orchestrator.generate_draft(
        normalized_text=normalized_text,
        issue_type=issue_type,
        risk_flags=risk_flags,
        severity=severity,
        must_human_review=must_human_review,
        evidence_candidates=evidence_candidates,
    )


__all__ = [
    "BaseAgent",
    "BaseSpecialist",
    "BillingSpecialist",
    "ComplaintAgent",
    "DefaultAgent",
    "GeneralSpecialist",
    "LogisticsAgent",
    "Orchestrator",
    "RefundAgent",
    "TechnicalAgent",
    "generate_draft_with_orchestrator",
    "get_orchestrator",
]
