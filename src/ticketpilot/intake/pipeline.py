"""Intake pipeline for ticket normalization and entity extraction."""

from datetime import datetime, timezone, timezone

from ticketpilot.schema.ticket import NormalizedTicket, RawTicket
from ticketpilot.intake.normalizer import TextNormalizer
from ticketpilot.intake.entity_extractor import EntityExtractor


def pipeline(raw_ticket: RawTicket) -> NormalizedTicket:
    """
    Process raw ticket through intake pipeline.

    Args:
        raw_ticket: RawTicket to process

    Returns:
        NormalizedTicket with cleaned text and extracted entities
    """
    normalizer = TextNormalizer()
    extractor = EntityExtractor()

    # Normalize text
    cleaned_text = normalizer.normalize(raw_ticket.original_text)

    # Extract entities
    entities = extractor.extract(cleaned_text)

    return NormalizedTicket(
        text=cleaned_text,
        language="zh" if cleaned_text and any('一' <= c <= '鿿' for c in cleaned_text) else "unknown",
        order_numbers=entities.order_numbers,
        product_info=entities.product_info,
        amount=entities.amount,
        cleaned_at=datetime.now(timezone.utc),
    )
