"""JSONL-based optimization history for the auto-optimizer.

Stores each optimization iteration as a single JSON line, enabling
append-only writes, fast reads, and ``--continue`` support via a
companion state.json file.
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any

from ticketpilot.optimizer.config import OptimizerConfig

logger = logging.getLogger(__name__)


class OptimizationHistory:
    """Append-only JSONL log of optimization iterations.

    Each record is a dict that is serialized as one JSON line.
    A companion ``state.json`` tracks the current iteration index
    and baseline composite score for ``--continue`` support.

    Usage::

        history = OptimizationHistory(config)
        history.init(clear=True)          # create / reset files
        history.record({...})             # append one iteration
        iters = history.load()            # read all
        last = history.get_last()         # most recent
        state = history.get_state()       # resume state
        history.save_state({"iteration": 5, "composite": 0.87})
    """

    def __init__(self, config: OptimizerConfig | None = None):
        self.config = config or OptimizerConfig()
        self._jsonl_path: pathlib.Path = self.config.history_jsonl
        self._state_path: pathlib.Path = self.config.state_json

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def init(self, *, clear: bool = False) -> None:
        """Create (or clear) the JSONL history and state files.

        Args:
            clear: If ``True``, truncate existing files so the history
                   starts fresh.  Defaults to ``False`` (append mode).
        """
        if clear:
            # Truncate history
            self._jsonl_path.write_text("", encoding="utf-8")
            logger.info("Cleared history file: %s", self._jsonl_path)

        # Ensure parent dirs exist
        self._jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.parent.mkdir(parents=True, exist_ok=True)

        # Create empty state if it doesn't exist
        if not self._state_path.exists() or clear:
            self._state_path.write_text(
                json.dumps({"iteration": 0, "composite": 0.0}),
                encoding="utf-8",
            )
            logger.info("Initialized state file: %s", self._state_path)

    # ------------------------------------------------------------------
    # Record append
    # ------------------------------------------------------------------

    def record(self, iteration_data: dict[str, Any]) -> None:
        """Append one iteration record to the JSONL file.

        The record is serialized as a single JSON line terminated by ``\\n``.

        Args:
            iteration_data: Arbitrary dict (must be JSON-serializable).
        """
        line = json.dumps(iteration_data, ensure_ascii=False, default=str)
        with self._jsonl_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        logger.debug("Recorded iteration to %s", self._jsonl_path)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    def load(self) -> list[dict[str, Any]]:
        """Read all iteration records from the JSONL file.

        Returns:
            List of dicts in file order (oldest first).
        """
        if not self._jsonl_path.exists():
            return []

        records: list[dict[str, Any]] = []
        with self._jsonl_path.open("r", encoding="utf-8") as f:
            for line_no, raw_line in enumerate(f, start=1):
                stripped = raw_line.strip()
                if not stripped:
                    continue
                try:
                    records.append(json.loads(stripped))
                except json.JSONDecodeError:
                    logger.warning(
                        "Skipping malformed JSONL line %d in %s",
                        line_no,
                        self._jsonl_path,
                    )
        return records

    def get_last(self) -> dict[str, Any] | None:
        """Return the most recent iteration record, or ``None`` if empty."""
        records = self.load()
        return records[-1] if records else None

    # ------------------------------------------------------------------
    # State management (--continue support)
    # ------------------------------------------------------------------

    def get_state(self) -> dict[str, Any]:
        """Load the optimizer state from ``state.json``.

        Returns:
            Dict with at least ``iteration`` (int) and ``composite`` (float).
            Returns a default ``{"iteration": 0, "composite": 0.0}`` when the
            file is missing or malformed.
        """
        default = {"iteration": 0, "composite": 0.0}
        if not self._state_path.exists():
            return default
        try:
            return json.loads(self._state_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            logger.warning("Corrupt state file %s, resetting", self._state_path)
            return default

    def save_state(self, state: dict[str, Any]) -> None:
        """Persist optimizer state to ``state.json``.

        Args:
            state: Dict to write (must be JSON-serializable).
        """
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        logger.debug("Saved state to %s", self._state_path)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @property
    def iteration_count(self) -> int:
        """Number of recorded iterations."""
        return len(self.load())
