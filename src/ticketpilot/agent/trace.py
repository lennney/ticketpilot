"""Agent Trace — append-only run-level event recording."""

from __future__ import annotations

import copy
from typing import Any

from ticketpilot.agent.schemas import AgentEvent, AgentEventType


class AgentTrace:
    """Append-only record of events for a single agent run.

    Events are recorded in insertion order and cannot be modified
    or deleted after being added. The internal list is not exposed
    directly; callers receive copies via get_events().
    """

    def __init__(self, run_id: str) -> None:
        if not run_id or not run_id.strip():
            raise ValueError("run_id must not be empty")
        self._run_id = run_id
        self._events: list[AgentEvent] = []

    def add_event(
        self,
        event_type: AgentEventType,
        data: dict[str, Any] | None = None,
        step_number: int | None = None,
    ) -> AgentEvent:
        """Append a new event and return it."""
        event = AgentEvent(
            event_type=event_type,
            data=data or {},
            step_number=step_number,
        )
        self._events.append(event)
        return event

    def get_events(self) -> list[AgentEvent]:
        """Return a copy of all recorded events."""
        return copy.deepcopy(self._events)

    def to_json(self) -> str:
        """Serialize the trace to a JSON string."""
        payload = self.to_dict()
        import json

        return json.dumps(payload, default=str, ensure_ascii=False)

    def to_dict(self) -> dict[str, Any]:
        """Return the trace as a JSON-compatible dict."""
        return {
            "run_id": self._run_id,
            "events": [e.model_dump(mode="json") for e in self._events],
            "event_count": len(self._events),
        }

    def count(self) -> int:
        """Return the number of recorded events."""
        return len(self._events)

    def last_event(self) -> AgentEvent | None:
        """Return the most recent event, or None if no events exist."""
        if not self._events:
            return None
        return copy.deepcopy(self._events[-1])
