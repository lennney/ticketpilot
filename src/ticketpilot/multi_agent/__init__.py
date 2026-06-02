"""
Multi-Agent Orchestrator for TicketPilot.

Routes tickets to specialized agents based on intent:
- RefundAgent: Handles refund-related tickets
- ComplaintAgent: Handles complaints and escalations
- LogisticsAgent: Handles shipping and delivery issues
- TechnicalAgent: Handles technical issues
- DefaultAgent: Handles other intents
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ticketpilot.drafting.draft_agent import DraftAgent
from ticketpilot.drafting.schemas import DraftReply
from ticketpilot.schema.evidence import EvidenceCandidate

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for specialized agents."""
    
    def __init__(self, name: str):
        self.name = name
        self._draft_agent = DraftAgent()
    
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
        super().__init__("RefundAgent")
    
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
        # Use DraftAgent with refund-specific context
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
        super().__init__("ComplaintAgent")
    
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
        super().__init__("LogisticsAgent")
    
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
        super().__init__("TechnicalAgent")
    
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
        super().__init__("DefaultAgent")
    
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


@dataclass
class AgentRoute:
    """Route configuration for an agent."""
    intent: str
    agent: BaseAgent
    priority: int = 0  # Higher priority = preferred agent


class Orchestrator:
    """
    Multi-Agent Orchestrator.
    
    Routes tickets to specialized agents based on intent.
    """
    
    def __init__(self):
        # Initialize specialized agents
        self._agents = {
            "refund": RefundAgent(),
            "return_exchange": RefundAgent(),  # Same agent for returns
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
        
        Args:
            normalized_text: Customer's normalized message text.
            issue_type: Classified intent / issue type.
            risk_flags: Detected risk flags.
            severity: Risk severity level.
            must_human_review: Whether risk assessment requires human review.
            evidence_candidates: Pre-retrieved evidence.
        
        Returns:
            DraftReply with citations, confidence, and guard flags.
        """
        # Get the appropriate agent
        agent = self.get_agent(issue_type)
        
        logger.info(
            "Orchestrator: routing to %s for intent=%s",
            agent.name,
            issue_type,
        )
        
        # Generate draft using the specialized agent
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
