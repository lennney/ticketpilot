"""
Agent tracing module for observability.

Provides structured tracing for DraftAgent calls, recording:
- Input/output
- Each step's duration and results
- Token usage and cost estimates
- Error tracking
"""
from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class StepTrace:
    """Trace for a single step in the agent loop."""
    name: str
    start_time: float
    end_time: float | None = None
    duration_ms: float | None = None
    input_data: dict[str, Any] | None = None
    output_data: dict[str, Any] | None = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def finish(self, output_data: dict[str, Any] | None = None, error: str | None = None) -> None:
        """Mark step as finished."""
        self.end_time = time.time()
        self.duration_ms = (self.end_time - self.start_time) * 1000
        if output_data:
            self.output_data = output_data
        if error:
            self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "duration_ms": round(self.duration_ms, 2) if self.duration_ms else None,
            "input": self.input_data,
            "output": self.output_data,
            "error": self.error,
            "metadata": self.metadata,
        }


@dataclass
class AgentTrace:
    """Complete trace for an agent call."""
    trace_id: str
    timestamp: datetime
    agent_name: str
    input_data: dict[str, Any]
    steps: list[StepTrace] = field(default_factory=list)
    output_data: dict[str, Any] | None = None
    error: str | None = None
    total_duration_ms: float | None = None
    metrics: dict[str, Any] = field(default_factory=dict)
    start_time: float = field(default_factory=time.time)

    @contextmanager
    def step(self, name: str, input_data: dict[str, Any] | None = None):
        """Context manager for tracing a step."""
        step_trace = StepTrace(
            name=name,
            start_time=time.time(),
            input_data=input_data,
        )
        self.steps.append(step_trace)
        try:
            yield step_trace
        except Exception as e:
            step_trace.finish(error=str(e))
            raise
        else:
            if step_trace.end_time is None:
                step_trace.finish()

    def finish(self, output_data: dict[str, Any] | None = None, error: str | None = None) -> None:
        """Mark trace as finished."""
        self.total_duration_ms = (time.time() - self.start_time) * 1000
        if output_data:
            self.output_data = output_data
        if error:
            self.error = error

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "trace_id": self.trace_id,
            "timestamp": self.timestamp.isoformat(),
            "agent_name": self.agent_name,
            "input": self.input_data,
            "steps": [s.to_dict() for s in self.steps],
            "output": self.output_data,
            "error": self.error,
            "total_duration_ms": round(self.total_duration_ms, 2) if self.total_duration_ms else None,
            "metrics": self.metrics,
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    def save(self, directory: str | Path = "logs/traces") -> Path:
        """Save trace to file."""
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        
        file_path = dir_path / f"{self.trace_id}.json"
        file_path.write_text(self.to_json(), encoding="utf-8")
        return file_path


class TraceCollector:
    """Collects and manages agent traces."""
    
    def __init__(self, log_dir: str = "logs/traces", max_traces: int = 1000):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.max_traces = max_traces
        self._traces: list[AgentTrace] = []
    
    def create_trace(self, agent_name: str, input_data: dict[str, Any]) -> AgentTrace:
        """Create a new trace."""
        trace = AgentTrace(
            trace_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            agent_name=agent_name,
            input_data=input_data,
        )
        self._traces.append(trace)
        
        # Trim old traces if needed
        if len(self._traces) > self.max_traces:
            self._traces = self._traces[-self.max_traces:]
        
        return trace
    
    def save_trace(self, trace: AgentTrace) -> Path:
        """Save a trace to file."""
        return trace.save(self.log_dir)
    
    def get_recent_traces(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent traces."""
        return [t.to_dict() for t in self._traces[-limit:]]
    
    def get_stats(self) -> dict[str, Any]:
        """Get trace statistics."""
        if not self._traces:
            return {"total": 0}
        
        durations = [t.total_duration_ms for t in self._traces if t.total_duration_ms]
        errors = sum(1 for t in self._traces if t.error)
        
        return {
            "total": len(self._traces),
            "errors": errors,
            "avg_duration_ms": round(sum(durations) / len(durations), 2) if durations else 0,
            "max_duration_ms": round(max(durations), 2) if durations else 0,
            "min_duration_ms": round(min(durations), 2) if durations else 0,
        }


# Global trace collector
_collector: TraceCollector | None = None


def get_trace_collector() -> TraceCollector:
    """Get or create the global trace collector."""
    global _collector
    if _collector is None:
        _collector = TraceCollector()
    return _collector


def create_trace(agent_name: str, input_data: dict[str, Any]) -> AgentTrace:
    """Create a new trace using the global collector."""
    return get_trace_collector().create_trace(agent_name, input_data)
