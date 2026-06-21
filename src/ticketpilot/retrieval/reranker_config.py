"""Configuration for the hybrid reranker.

Defines signal weights, intent boost tables, and content quality parameters.
Supports loading from YAML files for A/B experiments.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ContentQualityConfig:
    """Parameters for the content quality scoring signal."""

    optimal_length_min: int = 200
    optimal_length_max: int = 800
    keyword_density_weight: float = 0.5

    def __post_init__(self) -> None:
        if self.optimal_length_min > self.optimal_length_max:
            raise ValueError(
                f"optimal_length_min ({self.optimal_length_min}) must be <= "
                f"optimal_length_max ({self.optimal_length_max})"
            )
        if not 0 <= self.keyword_density_weight <= 1:
            raise ValueError(
                f"keyword_density_weight must be between 0 and 1, "
                f"got {self.keyword_density_weight}"
            )


@dataclass
class RerankerConfig:
    """Configuration for the hybrid reranker.

    Attributes:
        weights: Signal name -> weight mapping. Must sum to 1.0.
        intent_boost_table: IntentClass value -> {doc_type: boost_value}.
        content_quality: Content quality scoring parameters.
        num_query_variants: Number of LLM-generated query variants.
    """

    weights: dict[str, float] = field(default_factory=dict)
    intent_boost_table: dict[str, dict[str, float]] = field(default_factory=dict)
    content_quality: ContentQualityConfig = field(default_factory=ContentQualityConfig)
    num_query_variants: int = 2

    # --- Validation ---

    def validate(self) -> None:
        """Validate config. Raises ValueError on issues."""
        if not self.weights:
            raise ValueError("weights cannot be empty")
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                f"weights must sum to 1.0, got {total:.4f}: {self.weights}"
            )
        for name, w in self.weights.items():
            if w < 0:
                raise ValueError(f"weight '{name}' must be >= 0, got {w}")

    # --- Factories ---

    @classmethod
    def default(cls) -> RerankerConfig:
        """Default config with balanced weights."""
        cfg = cls(
            weights={
                "rrf_score": 0.40,
                "embedding_similarity": 0.25,
                "intent_metadata_boost": 0.20,
                "content_quality": 0.15,
            },
            intent_boost_table={
                "refund": {"policy": 0.15, "faq": 0.10},
                "return_exchange": {"policy": 0.15, "faq": 0.10},
                "account_issue": {"policy": 0.10, "faq": 0.10},
                "technical_issue": {"faq": 0.10, "case": 0.10},
                "product_consulting": {"faq": 0.15},
                "logistics": {"faq": 0.10, "case": 0.10},
                "complaint": {"case": 0.15, "policy": 0.10},
                "other": {},
            },
            content_quality=ContentQualityConfig(
                optimal_length_min=200,
                optimal_length_max=800,
                keyword_density_weight=0.5,
            ),
            num_query_variants=2,
        )
        cfg.validate()
        return cfg

    @classmethod
    def from_yaml(cls, path: str | Path) -> RerankerConfig:
        """Load config from a YAML file.

        Falls back to default if file not found.
        """
        import logging  # noqa: PLC0415
        import yaml  # noqa: PLC0415

        logger = logging.getLogger(__name__)
        path = Path(path)
        if not path.exists():
            logger.warning("Reranker config file not found: %s, using defaults", path)
            return cls.default()

        with path.open("r", encoding="utf-8") as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}

        weights = data.get("weights", {})
        intent_boost = data.get("intent_boost", {})
        cq_data = data.get("content_quality", {})
        num_variants = data.get("num_query_variants", 2)

        cq = ContentQualityConfig(
            optimal_length_min=cq_data.get("optimal_length_min", 200),
            optimal_length_max=cq_data.get("optimal_length_max", 800),
            keyword_density_weight=cq_data.get("keyword_density_weight", 0.5),
        )

        cfg = cls(
            weights=weights,
            intent_boost_table=intent_boost,
            content_quality=cq,
            num_query_variants=num_variants,
        )
        cfg.validate()
        return cfg

    # --- Helpers ---

    def get_intent_boost(self, intent: str | None, doc_type: str) -> float:
        """Get boost value for an intent+doc_type combination."""
        if intent is None:
            return 0.0
        # Normalize doc_type to lowercase for table lookup
        dt_lower = doc_type.lower() if doc_type else ""
        return self.intent_boost_table.get(intent, {}).get(dt_lower, 0.0)

    def adjust_weights_for_missing_signals(
        self, unavailable_signals: set[str]
    ) -> dict[str, float]:
        """Redistribute weights when signals are unavailable.

        Returns a new weight dict with unavailable signals removed
        and remaining weights renormalized to sum to 1.0.
        """
        if not unavailable_signals:
            return dict(self.weights)

        available = {
            k: v for k, v in self.weights.items() if k not in unavailable_signals
        }
        total = sum(available.values())
        if total <= 0:
            # Fallback: equal weight on all available
            n = len(available) or 1
            return {k: 1.0 / n for k in available}

        return {k: v / total for k, v in available.items()}
