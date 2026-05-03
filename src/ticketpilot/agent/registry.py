"""Agent Tool Registry — runtime callable binding layer.

RegisteredTool uses a dataclass (not Pydantic) to keep the callable
handler separate from the data-only AgentToolSpec schema.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from ticketpilot.agent.schemas import AgentToolSpec


@dataclass(frozen=True)
class RegisteredTool:
    """A registered tool binding a data-only spec to a runtime handler."""

    spec: AgentToolSpec
    handler: Callable[[dict[str, Any]], Any]

    def __post_init__(self) -> None:
        if not callable(self.handler):
            raise TypeError("handler must be callable")


class ToolRegistry:
    """Deterministic, side-effect-free registry for agent tools."""

    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(self, tool: RegisteredTool) -> None:
        """Register a tool. Raises ValueError on duplicate name."""
        name = tool.spec.name
        if name in self._tools:
            raise ValueError(f"tool already registered: '{name}'")
        self._tools[name] = tool

    def get(self, name: str) -> RegisteredTool:
        """Look up a registered tool by name. Raises KeyError if unknown."""
        if name not in self._tools:
            raise KeyError(f"unknown tool: '{name}'")
        return self._tools[name]

    def has(self, name: str) -> bool:
        """Return True if a tool with *name* is registered."""
        return name in self._tools

    def list_names(self) -> list[str]:
        """Return registered tool names in insertion order."""
        return list(self._tools.keys())

    def list_specs(self) -> list[AgentToolSpec]:
        """Return specs of all registered tools in insertion order."""
        return [t.spec for t in self._tools.values()]

    def call(self, name: str, input_data: dict[str, Any]) -> Any:
        """Invoke a registered tool's handler with *input_data*.

        Raises KeyError if the tool is not registered.
        Trace recording belongs to the Batch 3 runtime loop.
        """
        tool = self.get(name)
        return tool.handler(input_data)
