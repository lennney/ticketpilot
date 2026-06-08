"""Unit tests for RerankerConfig."""
import tempfile
from pathlib import Path

import pytest

from ticketpilot.retrieval.reranker_config import ContentQualityConfig, RerankerConfig


class TestRerankerConfigValidation:
    def test_default_config_is_valid(self):
        cfg = RerankerConfig.default()
        cfg.validate()  # should not raise

    def test_weights_sum_to_one(self):
        cfg = RerankerConfig.default()
        total = sum(cfg.weights.values())
        assert abs(total - 1.0) < 1e-6

    def test_empty_weights_raises(self):
        cfg = RerankerConfig(weights={})
        with pytest.raises(ValueError, match="weights cannot be empty"):
            cfg.validate()

    def test_weights_not_summing_raises(self):
        cfg = RerankerConfig(weights={"a": 0.3, "b": 0.3})
        with pytest.raises(ValueError, match="must sum to 1.0"):
            cfg.validate()

    def test_negative_weight_raises(self):
        cfg = RerankerConfig(weights={"a": 1.5, "b": -0.5})
        with pytest.raises(ValueError, match="must be >= 0"):
            cfg.validate()


class TestRerankerConfigFromYaml:
    def test_load_from_yaml(self, tmp_path):
        yaml_content = """\
weights:
  rrf_score: 0.50
  embedding_similarity: 0.30
  intent_metadata_boost: 0.10
  content_quality: 0.10

intent_boost:
  refund:
    policy: 0.20

content_quality:
  optimal_length_min: 100
  optimal_length_max: 600
  keyword_density_weight: 0.3

num_query_variants: 3
"""
        p = tmp_path / "reranker.yaml"
        p.write_text(yaml_content)
        cfg = RerankerConfig.from_yaml(str(p))
        assert cfg.weights["rrf_score"] == 0.50
        assert cfg.num_query_variants == 3
        assert cfg.content_quality.optimal_length_min == 100

    def test_missing_file_returns_default(self):
        cfg = RerankerConfig.from_yaml("/nonexistent/path.yaml")
        assert cfg.weights == RerankerConfig.default().weights


class TestRerankerConfigHelpers:
    def test_get_intent_boost_match(self):
        cfg = RerankerConfig.default()
        boost = cfg.get_intent_boost("refund", "policy")
        assert boost == 0.15

    def test_get_intent_boost_no_match(self):
        cfg = RerankerConfig.default()
        boost = cfg.get_intent_boost("refund", "case")
        assert boost == 0.0

    def test_get_intent_boost_none_intent(self):
        cfg = RerankerConfig.default()
        boost = cfg.get_intent_boost(None, "policy")
        assert boost == 0.0

    def test_adjust_weights_no_missing(self):
        cfg = RerankerConfig.default()
        adjusted = cfg.adjust_weights_for_missing_signals(set())
        assert adjusted == cfg.weights

    def test_adjust_weights_embedding_missing(self):
        cfg = RerankerConfig.default()
        adjusted = cfg.adjust_weights_for_missing_signals({"embedding_similarity"})
        assert "embedding_similarity" not in adjusted
        total = sum(adjusted.values())
        assert abs(total - 1.0) < 1e-6

    def test_adjust_weights_preserves_proportions(self):
        cfg = RerankerConfig.default()
        adjusted = cfg.adjust_weights_for_missing_signals({"embedding_similarity"})
        # rrf was 0.40, now should be 0.40/0.75 ≈ 0.533
        expected_ratio = 0.40 / 0.75
        assert abs(adjusted["rrf_score"] - expected_ratio) < 1e-6
