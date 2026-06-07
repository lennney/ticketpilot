"""CitationValidator for unsupported claim detection.

Uses deterministic rules (not NLP) to validate citations and detect
claims in draft text that lack citation backing.
"""

import re

from ticketpilot.drafting.schemas import Citation
from ticketpilot.schema.evidence import EvidenceCandidate

# Keywords that indicate a factual claim in Chinese customer service replies.
# When a sentence contains one of these keywords and lacks a [N] citation marker,
# it is flagged as potentially unsupported.
_CLAIM_KEYWORDS: list[str] = [
    "承诺退款金额",
    "赔偿金额为",
    "根据法律规定",
    "根据政策",
    "根据相关政策",
    "根据规定",
    "根据公司",
    "按照政策规定",
    "保证退款",
    "保证赔偿",
    "可以退款",
    "赔偿",
]

_SENTENCE_SPLIT = re.compile(r"[。！？!?]")


class CitationValidator:
    """Deterministic validator for citation correctness and claim coverage.

    Performs two checks:
    1. Citation existence: every [N] in draft_text has a corresponding citation.
    2. Claim-coverage scan: sentences with claim keywords but no citation marker.
    """

    def validate(
        self,
        text: str,
        citations: list[Citation],
        evidence_candidates: list[EvidenceCandidate] | None = None,
    ) -> tuple[bool, list[str]]:
        """Validate citations and detect unsupported claims.

        Args:
            text: The draft reply text to validate.
            citations: Citation objects from the draft.
            evidence_candidates: Original evidence candidates for cross-reference.

        Returns:
            (passed, issues) tuple. passed=True when no issues found.
        """
        issues: list[str] = []

        # Check 1: citation existence — every [N] in text has a citation
        citation_markers = re.findall(r"\[(\d+)\]", text)
        for marker in citation_markers:
            idx = int(marker)
            if idx < 1 or idx > len(citations):
                issues.append(
                    f"Citation marker [{idx}] exceeds available citations ({len(citations)})"
                )

        # Check 2: claim-coverage scan — sentences with claim keywords but no [N]
        sentences = _SENTENCE_SPLIT.split(text)
        for sentence in sentences:
            stripped = sentence.strip()
            if not stripped:
                continue
            has_marker = "[" in stripped and "]" in stripped
            has_keyword = any(kw in stripped for kw in _CLAIM_KEYWORDS)
            if has_keyword and not has_marker:
                issues.append(
                    f"Potential unsupported claim in sentence: "
                    f"'{stripped[:80]}'"
                )

        # Check 3: cross-reference citations against evidence (if provided)
        if evidence_candidates is not None:
            valid_chunk_ids = {ec.chunk_id for ec in evidence_candidates}
            for c in citations:
                if c.chunk_id not in valid_chunk_ids:
                    issues.append(
                        f"Citation references unknown chunk_id: {c.chunk_id}"
                    )

        return (len(issues) == 0, issues)

    def has_unsupported_claims(self, text: str, citations: list[Citation]) -> bool:
        """Quick check: does the text contain likely unsupported claims?"""
        passed, _ = self.validate(text, citations)
        return not passed
