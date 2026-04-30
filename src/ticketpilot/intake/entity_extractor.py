"""Entity extraction for ticket intake."""

import re
from dataclasses import dataclass


@dataclass
class ExtractedEntities:
    """Entities extracted from ticket text."""

    order_numbers: list[str]
    product_info: str | None
    amount: float | None


class EntityExtractor:
    """Extracts structured entities from normalized ticket text."""

    # Regex patterns for entity extraction
    ORDER_NUMBER_PATTERNS = [
        r"订单号[:：]?\s*(\d+)",
        r"订单\s*号[:：]?\s*(\d+)",
        r"单号[:：]?\s*(\d+)",
        r"订单[:：]?\s*(\d{6,})",
    ]

    def extract(self, text: str) -> ExtractedEntities:
        """
        Extract entities from ticket text.

        Args:
            text: Normalized ticket text

        Returns:
            ExtractedEntities with order numbers, product info, and amount
        """
        order_numbers = self._extract_order_numbers(text)

        return ExtractedEntities(
            order_numbers=order_numbers,
            product_info=None,
            amount=None,
        )

    def _extract_order_numbers(self, text: str) -> list[str]:
        """Extract order numbers from text using regex patterns."""
        order_numbers = []
        for pattern in self.ORDER_NUMBER_PATTERNS:
            matches = re.findall(pattern, text)
            order_numbers.extend(matches)
        # Remove duplicates while preserving order
        seen = set()
        unique_orders = []
        for order in order_numbers:
            if order not in seen:
                seen.add(order)
                unique_orders.append(order)
        return unique_orders
