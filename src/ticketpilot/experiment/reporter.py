"""Experiment report with comparison table."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ExperimentReport(BaseModel):
    """Report comparing control vs treatment results.

    Attributes:
        experiment_id: Links back to ExperimentConfig.
        name: Experiment name.
        timestamp: When the experiment was run.
        control_results: Metrics for the control group.
        treatment_results: Metrics for the treatment group.
        delta: Differences (treatment - control).
    """

    experiment_id: str
    name: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    control_results: dict[str, Any] = Field(default_factory=dict)
    treatment_results: dict[str, Any] = Field(default_factory=dict)
    delta: dict[str, Any] = Field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        return self.model_dump(mode="json")

    def to_json(self, indent: int = 2) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def save(self, path: str | Path) -> None:
        """Write report as JSON to *path*."""
        Path(path).write_text(self.to_json(), encoding="utf-8")

    def to_markdown(self) -> str:
        """Render a Markdown comparison table."""
        lines = [
            f"# Experiment: {self.name}",
            f"**ID:** {self.experiment_id}  ",
            f"**Run at:** {self.timestamp.isoformat()}  ",
            "",
            "| Metric | Control | Treatment | Delta |",
            "|--------|---------|-----------|-------|",
        ]

        all_keys = sorted(set(self.control_results) | set(self.treatment_results))
        for key in all_keys:
            c = self.control_results.get(key, "N/A")
            t = self.treatment_results.get(key, "N/A")
            d = self.delta.get(key, "N/A")
            # Format numbers nicely
            c_str = f"{c:.4f}" if isinstance(c, float) else str(c)
            t_str = f"{t:.4f}" if isinstance(t, float) else str(t)
            d_str = f"{d:+.4f}" if isinstance(d, float) else str(d)
            lines.append(f"| {key} | {c_str} | {t_str} | {d_str} |")

        return "\n".join(lines)
