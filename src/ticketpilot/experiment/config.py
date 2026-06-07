"""Experiment configuration model."""

from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field


class ExperimentConfig(BaseModel):
    """Configuration for an A/B experiment.

    Attributes:
        experiment_id: Unique identifier (auto-generated UUID).
        name: Human-readable experiment name.
        control: Config overrides for the control group.
        treatment: Config overrides for the treatment group.
        description: What this experiment tests.
    """

    experiment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    control: dict[str, Any] = Field(default_factory=dict)
    treatment: dict[str, Any] = Field(default_factory=dict)
    description: str = ""
