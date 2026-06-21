"""SQLite-backed agent run state persistence.

Factor 6: Launch / Pause / Resume

Provides save, load, pause, resume, list, and delete operations
for AgentRun objects. State is stored as JSON in SQLite for simplicity
and portability.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ticketpilot.agent.schemas import AgentRun, AgentRunStatus


class AgentStateStore:
    """SQLite-backed agent run state persistence.

    Usage:
        store = AgentStateStore("agent_runs.db")
        store.save_run(agent_run)
        loaded = store.load_run(run_id)
        store.pause_run(run_id, reason="waiting_for_human_input")
        resumed = store.resume_run(run_id, human_input={"decision": "approve"})
    """

    def __init__(self, db_path: str | Path = "agent_runs.db") -> None:
        self._db_path = str(db_path)
        self._init_db()

    def _init_db(self) -> None:
        """Create the runs table if it doesn't exist."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_runs (
                    run_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    run_data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    pause_reason TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_status
                ON agent_runs(status)
            """)
            conn.commit()

    def save_run(self, run: AgentRun) -> None:
        """Save or overwrite an AgentRun."""
        now = datetime.now(timezone.utc).isoformat()
        data = run.model_dump_json()

        with sqlite3.connect(self._db_path) as conn:
            conn.execute(
                """INSERT OR REPLACE INTO agent_runs
                   (run_id, status, run_data, created_at, updated_at, pause_reason)
                   VALUES (?, ?, ?, ?, ?, NULL)""",
                (run.run_id, run.final_status.value, data, now, now),
            )
            conn.commit()

    def load_run(self, run_id: str) -> AgentRun | None:
        """Load an AgentRun by run_id. Returns None if not found."""
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT run_data FROM agent_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()

        if row is None:
            return None

        return AgentRun.model_validate_json(row[0])

    def pause_run(self, run_id: str, reason: str = "") -> None:
        """Mark a run as paused with an optional reason."""
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT run_data FROM agent_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()

            if row is None:
                raise ValueError(f"Run {run_id} not found")

            run = AgentRun.model_validate_json(row[0])
            run.final_status = AgentRunStatus.PAUSED

            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """UPDATE agent_runs
                   SET status = ?, run_data = ?, updated_at = ?, pause_reason = ?
                   WHERE run_id = ?""",
                (
                    AgentRunStatus.PAUSED.value,
                    run.model_dump_json(),
                    now,
                    reason,
                    run_id,
                ),
            )
            conn.commit()

    def resume_run(self, run_id: str, human_input: dict[str, Any]) -> AgentRun:
        """Resume a paused run with human input.

        Args:
            run_id: The run to resume.
            human_input: Human decision/context to inject.

        Returns:
            The resumed AgentRun with status set to RUNNING.

        Raises:
            ValueError: If run is not found or not in PAUSED status.
        """
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute(
                "SELECT run_data FROM agent_runs WHERE run_id = ?",
                (run_id,),
            ).fetchone()

            if row is None:
                raise ValueError(f"Run {run_id} not found")

            run = AgentRun.model_validate_json(row[0])

            if run.final_status != AgentRunStatus.PAUSED:
                raise ValueError(
                    f"Run {run_id} is not paused (status: {run.final_status.value})"
                )

            run.final_status = AgentRunStatus.RUNNING
            run.review_decision = human_input

            now = datetime.now(timezone.utc).isoformat()
            conn.execute(
                """UPDATE agent_runs
                   SET status = ?, run_data = ?, updated_at = ?, pause_reason = NULL
                   WHERE run_id = ?""",
                (AgentRunStatus.RUNNING.value, run.model_dump_json(), now, run_id),
            )
            conn.commit()

        return run

    def list_paused(self) -> list[AgentRun]:
        """List all runs in PAUSED status."""
        return self.list_runs(status=AgentRunStatus.PAUSED)

    def list_runs(self, status: AgentRunStatus | None = None) -> list[AgentRun]:
        """List all runs, optionally filtered by status.

        Returns runs ordered by updated_at descending (most recent first).
        """
        with sqlite3.connect(self._db_path) as conn:
            if status:
                rows = conn.execute(
                    "SELECT run_data FROM agent_runs WHERE status = ? ORDER BY updated_at DESC",
                    (status.value,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT run_data FROM agent_runs ORDER BY updated_at DESC",
                ).fetchall()

        return [AgentRun.model_validate_json(row[0]) for row in rows]

    def delete_run(self, run_id: str) -> None:
        """Delete a run by run_id."""
        with sqlite3.connect(self._db_path) as conn:
            conn.execute("DELETE FROM agent_runs WHERE run_id = ?", (run_id,))
            conn.commit()

    @property
    def count(self) -> int:
        """Total number of stored runs."""
        with sqlite3.connect(self._db_path) as conn:
            row = conn.execute("SELECT COUNT(*) FROM agent_runs").fetchone()
            return row[0] if row else 0
