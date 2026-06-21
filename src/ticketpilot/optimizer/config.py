"""Optimizer configuration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# Project root (relative to this file)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# Default paths
DEFAULT_TICKETS_CSV = PROJECT_ROOT / "data" / "eval" / "tickets_eval.csv"
DEFAULT_GOLDEN_CSV = PROJECT_ROOT / "data" / "eval" / "golden_expectations.csv"
DEFAULT_HISTORY_JSONL = PROJECT_ROOT / "optimization_history.jsonl"
DEFAULT_STATE_JSON = PROJECT_ROOT / "optimization_state.json"
DEFAULT_REPORT_MD = PROJECT_ROOT / "reports" / "optimization" / "optimization_report.md"

# Composite score weights
COMPOSITE_WEIGHTS: dict[str, float] = {
    "intent": 0.25,
    "severity": 0.20,
    "risk_f1": 0.20,
    "evidence": 0.15,
    "no_auto_send": 0.10,
    "fallback": 0.10,
}

# Safety thresholds
MAX_SINGLE_METRIC_DROP = 0.02  # 2% — triggers rollback
MIN_CASES_FIXED = 1  # Must fix at least 1 case to keep the change

# Fix type priority (lower = safer, try first)
FIX_PRIORITY = {
    "confidence_threshold": 1,
    "confidence_weight": 1,
    "intent_keyword": 2,
    "risk_keyword": 2,
    "exclusion_rule": 2,  # NEW: same priority as keyword fixes
    "reranker_weight": 3,
    "knowledge_addition": 4,
    "code_change": 5,
}


@dataclass
class OptimizerConfig:
    """Runtime configuration for the optimizer."""

    max_rounds: int = 20
    diagnose_only: bool = False
    dry_run: bool = False
    resume: bool = False
    tickets_csv: Path = DEFAULT_TICKETS_CSV
    golden_csv: Path = DEFAULT_GOLDEN_CSV
    history_jsonl: Path = DEFAULT_HISTORY_JSONL
    state_json: Path = DEFAULT_STATE_JSON
    report_md: Path = DEFAULT_REPORT_MD
    weights: dict[str, float] = field(default_factory=lambda: dict(COMPOSITE_WEIGHTS))
    llm_api_key: str = ""
    llm_base_url: str = ""
    llm_model: str = ""
