"""Text normalization for ticket intake."""

import re


class TextNormalizer:
    """Normalizes ticket text by cleaning and standardizing."""

    def normalize(self, text: str) -> str:
        """
        Normalize ticket text.

        - Strip leading/trailing whitespace
        - Collapse multiple whitespace characters into single space

        Args:
            text: Raw ticket text

        Returns:
            Normalized text string
        """
        if not text:
            return ""
        # Strip leading/trailing whitespace
        text = text.strip()
        # Collapse multiple whitespace to single space
        text = re.sub(r"\s+", " ", text)
        return text
