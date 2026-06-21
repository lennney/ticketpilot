"""Multi-dimensional confidence scoring for TicketPilot.

Combines 4 signals into a single confidence score:
- retrieval_confidence: quality of retrieval results (RRF scores)
- classification_confidence: classifier's own confidence
- citation_confidence: proportion of claims with citations
- evidence_density: how many chunks were retrieved vs expected

Deterministic, rule-based — no LLM calls.
"""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, Field

from ticketpilot.config import CONFIDENCE_HIGH, CONFIDENCE_LOW, CONFIDENCE_MEDIUM
from ticketpilot.schema.ticket import TicketOutput

if TYPE_CHECKING:
    from ticketpilot.drafting.schemas import DraftReply


class ConfidenceLevel(str, Enum):
    """Confidence level tiers."""

    HIGH = "high"  # > 0.8  → auto-send
    MEDIUM = "medium"  # 0.6-0.8 → auto-send with disclaimer
    LOW = "low"  # 0.4-0.6 → human review
    CRITICAL = "critical"  # < 0.4  → escalate to human


class ConfidenceBreakdown(BaseModel):
    """Detailed breakdown of confidence scoring."""

    retrieval_confidence: float = Field(
        ge=0, le=1, description="Retrieval quality score"
    )
    classification_confidence: float = Field(
        ge=0, le=1, description="Classifier confidence"
    )
    citation_confidence: float = Field(
        ge=0, le=1, description="Citation coverage ratio"
    )
    evidence_density: float = Field(
        ge=0, le=1, description="Retrieved/expected chunks ratio"
    )
    overall: float = Field(ge=0, le=1, description="Weighted combination")
    level: ConfidenceLevel = Field(description="Confidence tier")


# Weights for combining dimensions
WEIGHTS = {
    "retrieval": 0.35,
    "classification": 0.25,
    "citation": 0.25,
    "evidence_density": 0.15,
}

# Expected chunk counts per intent (for evidence_density calculation)
EXPECTED_CHUNKS_BY_INTENT = {
    "refund": 3,
    "shipping": 2,
    "complaint": 3,
    "inquiry": 2,
    "other": 2,
}

# Thresholds (aligned with config/__init__.py — imported from there)
# This module uses the same CONFIDENCE_HIGH/MEDIUM/LOW constants that
# drafting/schemas.py uses, so confidence threshold adjustments by the
# optimizer actually take effect.


def _classify_level(score: float) -> ConfidenceLevel:
    """Map overall score to confidence level using config thresholds."""
    if score >= CONFIDENCE_HIGH:
        return ConfidenceLevel.HIGH
    elif score >= CONFIDENCE_MEDIUM:
        return ConfidenceLevel.MEDIUM
    elif score >= CONFIDENCE_LOW:
        return ConfidenceLevel.LOW
    else:
        return ConfidenceLevel.CRITICAL


def _retrieval_confidence(ticket_output: TicketOutput) -> float:
    """Compute retrieval confidence from evidence candidates.

    Uses the best evidence score as the retrieval confidence signal.
    If no evidence, returns 0.0.
    """
    if not ticket_output.evidence_candidates:
        return 0.0
    scores = [ec.score for ec in ticket_output.evidence_candidates]
    if not scores:
        return 0.0
    return min(max(scores), 1.0)


def _classification_confidence(ticket_output: TicketOutput) -> float:
    """Extract classification confidence directly."""
    return ticket_output.classification.confidence


def _citation_confidence(draft: Optional[DraftReply]) -> float:
    """Compute citation coverage: claims with citations / total claims.

    If no draft available, returns 0.5 (neutral).
    If no citations, returns 0.0.
    """
    if draft is None:
        return 0.5
    if not draft.citations:
        return 0.0
    # Count claims that have citation backing
    supported = sum(1 for c in draft.citations if c.claim_supported)
    total = len(draft.citations)
    return supported / total if total > 0 else 0.0


def _evidence_density(ticket_output: TicketOutput) -> float:
    """Compute evidence density: retrieved / expected chunks.

    Returns min(ratio, 1.0) to cap at 1.0.
    """
    intent = (
        ticket_output.classification.intent.value
        if hasattr(ticket_output.classification.intent, "value")
        else str(ticket_output.classification.intent)
    )
    expected = EXPECTED_CHUNKS_BY_INTENT.get(intent, 2)
    retrieved = (
        len(ticket_output.evidence_candidates)
        if ticket_output.evidence_candidates
        else 0
    )
    return min(retrieved / expected, 1.0) if expected > 0 else 0.0


class ConfidenceScorer:
    """Multi-dimensional confidence scorer.

    Usage:
        scorer = ConfidenceScorer()
        breakdown = scorer.score(ticket_output, draft)
        print(breakdown.overall)  # 0.82
        print(breakdown.level)    # ConfidenceLevel.HIGH
    """

    def score(
        self,
        ticket_output: TicketOutput,
        draft: Optional[DraftReply] = None,
    ) -> ConfidenceBreakdown:
        """Compute multi-dimensional confidence score.

        Args:
            ticket_output: Pipeline output with classification + evidence.
            draft: Optional draft reply (for citation confidence).

        Returns:
            ConfidenceBreakdown with all dimensions and overall score.
        """
        r_conf = _retrieval_confidence(ticket_output)
        c_conf = _classification_confidence(ticket_output)
        cite_conf = _citation_confidence(draft)
        e_density = _evidence_density(ticket_output)

        overall = (
            WEIGHTS["retrieval"] * r_conf
            + WEIGHTS["classification"] * c_conf
            + WEIGHTS["citation"] * cite_conf
            + WEIGHTS["evidence_density"] * e_density
        )

        return ConfidenceBreakdown(
            retrieval_confidence=round(r_conf, 4),
            classification_confidence=round(c_conf, 4),
            citation_confidence=round(cite_conf, 4),
            evidence_density=round(e_density, 4),
            overall=round(overall, 4),
            level=_classify_level(overall),
        )
