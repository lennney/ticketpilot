"""Hybrid reranker combining multiple scoring signals.

Signals:
1. RRF score (from keyword + vector fusion)
2. Embedding similarity (cosine similarity, requires real embedding)
3. Intent metadata boost (intent -> doc_type matching)
4. Content quality (length appropriateness + keyword density)

All signals are normalized to [0, 1] and combined with configurable weights.
"""

from __future__ import annotations

import math
import re
import logging
from dataclasses import dataclass, field
from typing import Any, Optional
from uuid import UUID

from ticketpilot.retrieval.reranker_config import RerankerConfig
from ticketpilot.retrieval.traces import FusedResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Output dataclasses
# ---------------------------------------------------------------------------


@dataclass
class RerankSignal:
    """One scoring signal with its weight and raw/normalized values."""

    name: str
    weight: float
    raw_value: float
    normalized_value: float
    contribution: float  # weight * normalized_value


@dataclass
class RerankResult:
    """Reranked result with signal breakdown."""

    chunk_id: UUID
    doc_id: UUID
    doc_type: str
    content: str
    final_score: float
    signals: list[RerankSignal] = field(default_factory=list)
    rank: int = 0
    # Preserve original RRF info
    rrf_score: float = 0.0
    keyword_rank: Optional[int] = None
    keyword_contribution: Optional[float] = None
    vector_rank: Optional[int] = None
    vector_contribution: Optional[float] = None
    sources: list[str] = field(default_factory=list)

    def to_fused_result(self) -> FusedResult:
        """Convert back to FusedResult for downstream compatibility."""
        from ticketpilot.retrieval.schema.knowledge import DocType  # noqa: PLC0415

        return FusedResult(
            chunk_id=self.chunk_id,
            doc_id=self.doc_id,
            doc_type=DocType(self.doc_type)
            if isinstance(self.doc_type, str)
            else self.doc_type,
            content=self.content,
            rrf_score=self.rrf_score,
            keyword_rank=self.keyword_rank,
            keyword_contribution=self.keyword_contribution,
            vector_rank=self.vector_rank,
            vector_contribution=self.vector_contribution,
            sources=self.sources + ["hybrid_rerank"],
        )


# ---------------------------------------------------------------------------
# Signal computations
# ---------------------------------------------------------------------------


def _cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    dot = sum(a * b for a, b in zip(vec1, vec2))
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    if norm1 == 0 or norm2 == 0:
        return 0.0
    return dot / (norm1 * norm2)


def _length_score(length: int, opt_min: int, opt_max: int) -> float:
    """Score content length on a bell curve centered on [opt_min, opt_max].

    Returns 1.0 at the optimal midpoint, decaying for shorter/longer content.
    """
    if length <= 0:
        return 0.0
    midpoint = (opt_min + opt_max) / 2
    # Gaussian-like decay: sigma = (opt_max - opt_min) / 2
    sigma = max((opt_max - opt_min) / 2, 1)
    return math.exp(-0.5 * ((length - midpoint) / sigma) ** 2)


def _keyword_density(query: str, content: str) -> float:
    """Compute what fraction of query terms appear in content.

    Splits query by whitespace, checks each term's presence.
    Uses word boundary for Latin text, substring for CJK.
    """
    terms = [t.strip() for t in query.split() if t.strip()]
    if not terms or not content:
        return 0.0

    def _term_in_content(term: str) -> bool:
        # CJK characters: substring match (no word boundaries in Chinese/Japanese)
        if any("\u4e00" <= ch <= "\u9fff" for ch in term):
            return term in content
        # Latin text: word boundary match to avoid "art" matching "smart"
        return bool(re.search(r"\b" + re.escape(term) + r"\b", content, re.IGNORECASE))

    hits = sum(1 for t in terms if _term_in_content(t))
    return hits / len(terms)


def _normalize_minmax(values: list[float]) -> list[float]:
    """Min-max normalize a list of values to [0, 1]."""
    if not values:
        return []
    lo = min(values)
    hi = max(values)
    if hi - lo < 1e-12:
        return [0.5] * len(values)
    return [(v - lo) / (hi - lo) for v in values]


# ---------------------------------------------------------------------------
# HybridReranker
# ---------------------------------------------------------------------------


class HybridReranker:
    """Multi-signal reranker combining RRF, embedding, intent, and content signals."""

    def __init__(
        self,
        config: RerankerConfig | None = None,
        embedding_provider: Any | None = None,
    ) -> None:
        self._config = config or RerankerConfig.default()
        self._embedding_provider = embedding_provider

    def rerank(
        self,
        candidates: list[FusedResult],
        query: str,
        query_embedding: list[float] | None = None,
        intent: str | None = None,
        top_k: int = 10,
    ) -> list[RerankResult]:
        """Rerank candidates using weighted multi-signal fusion.

        Args:
            candidates: Fused results from RRF fusion.
            query: Original query text (for keyword density).
            query_embedding: Query embedding vector (for embedding similarity).
            intent: Classified intent string (for intent boost).
            top_k: Number of results to return.

        Returns:
            Reranked list of RerankResult, sorted by final_score descending.
        """
        if not candidates:
            return []

        # Determine which signals are available
        has_embedding = (
            query_embedding is not None
            and len(query_embedding) > 0
            and self._embedding_provider is not None
        )
        # Check if using real (non-fake) embedding
        is_real_embedding = has_embedding and _is_real_embedding_provider(
            self._embedding_provider
        )

        unavailable: set[str] = set()
        if not is_real_embedding:
            unavailable.add("embedding_similarity")

        weights = self._config.adjust_weights_for_missing_signals(unavailable)

        # Compute raw signal values for all candidates
        rrf_scores = [c.rrf_score for c in candidates]
        norm_rrf = _normalize_minmax(rrf_scores)

        # Pre-compute doc embeddings if needed
        doc_embeddings: dict[UUID, list[float]] = {}
        if is_real_embedding:
            doc_embeddings = self._load_doc_embeddings([c.chunk_id for c in candidates])

        # Build rerank results
        results: list[RerankResult] = []
        for i, cand in enumerate(candidates):
            signals: list[RerankSignal] = []

            # Signal 1: RRF score
            w = weights.get("rrf_score", 0.0)
            raw = rrf_scores[i]
            norm = norm_rrf[i]
            signals.append(
                RerankSignal(
                    name="rrf_score",
                    weight=w,
                    raw_value=raw,
                    normalized_value=norm,
                    contribution=w * norm,
                )
            )

            # Signal 2: Embedding similarity
            w = weights.get("embedding_similarity", 0.0)
            if is_real_embedding and cand.chunk_id in doc_embeddings:
                sim = _cosine_similarity(query_embedding, doc_embeddings[cand.chunk_id])
            else:
                sim = 0.0
            signals.append(
                RerankSignal(
                    name="embedding_similarity",
                    weight=w,
                    raw_value=sim,
                    normalized_value=sim,  # already in [0,1]
                    contribution=w * sim,
                )
            )

            # Signal 3: Intent metadata boost
            w = weights.get("intent_metadata_boost", 0.0)
            boost = self._config.get_intent_boost(intent, cand.doc_type)
            # Normalize: boost is already a small positive value, cap at 1.0
            norm_boost = min(boost, 1.0)
            signals.append(
                RerankSignal(
                    name="intent_metadata_boost",
                    weight=w,
                    raw_value=boost,
                    normalized_value=norm_boost,
                    contribution=w * norm_boost,
                )
            )

            # Signal 4: Content quality
            w = weights.get("content_quality", 0.0)
            cq = self._config.content_quality
            len_score = _length_score(
                len(cand.content), cq.optimal_length_min, cq.optimal_length_max
            )
            kd = _keyword_density(query, cand.content)
            content_score = (
                1 - cq.keyword_density_weight
            ) * len_score + cq.keyword_density_weight * kd
            signals.append(
                RerankSignal(
                    name="content_quality",
                    weight=w,
                    raw_value=content_score,
                    normalized_value=content_score,
                    contribution=w * content_score,
                )
            )

            # Final score
            final = sum(s.contribution for s in signals)

            results.append(
                RerankResult(
                    chunk_id=cand.chunk_id,
                    doc_id=cand.doc_id,
                    doc_type=cand.doc_type.value
                    if hasattr(cand.doc_type, "value")
                    else str(cand.doc_type),
                    content=cand.content,
                    final_score=final,
                    signals=signals,
                    rrf_score=cand.rrf_score,
                    keyword_rank=cand.keyword_rank,
                    keyword_contribution=cand.keyword_contribution,
                    vector_rank=cand.vector_rank,
                    vector_contribution=cand.vector_contribution,
                    sources=list(cand.sources),
                )
            )

        # Sort by final_score descending
        results.sort(key=lambda r: r.final_score, reverse=True)

        # Assign ranks
        for i, r in enumerate(results[:top_k], 1):
            r.rank = i

        return results[:top_k]

    def _load_doc_embeddings(self, chunk_ids: list[UUID]) -> dict[UUID, list[float]]:
        """Load document embeddings from DB for the given chunk IDs."""
        embeddings: dict[UUID, list[float]] = {}
        if not chunk_ids:
            return embeddings
        try:
            from ticketpilot.retrieval.db.connection import get_db_connection  # noqa: PLC0415

            with get_db_connection() as conn:
                with conn.cursor() as cur:
                    placeholders = ",".join(["%s"] * len(chunk_ids))
                    cur.execute(
                        f"SELECT id, embedding FROM knowledge_chunks WHERE id IN ({placeholders})",
                        [str(cid) for cid in chunk_ids],
                    )
                    for row in cur.fetchall():
                        cid = UUID(row[0])
                        emb_str = row[1]
                        if emb_str:
                            if isinstance(emb_str, str):
                                emb_str = emb_str.strip("[]")
                                embeddings[cid] = [float(x) for x in emb_str.split(",")]
                            elif isinstance(emb_str, list):
                                embeddings[cid] = [float(x) for x in emb_str]
        except Exception as e:
            logger.warning("Failed to load document embeddings: %s", e)
        return embeddings


def _is_real_embedding_provider(provider: Any) -> bool:
    """Check if the embedding provider is a real (non-fake) provider."""
    if not hasattr(provider, "embed") and not hasattr(provider, "encode"):
        return False
    name = getattr(provider, "provider_name", "unknown")
    return name not in ("fake", "unknown", "")
