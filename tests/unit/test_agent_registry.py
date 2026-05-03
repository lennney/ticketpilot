"""Unit tests for Agent Tool Registry (Batch 2)."""

import pytest

from ticketpilot.agent.registry import RegisteredTool, ToolRegistry
from ticketpilot.agent.schemas import AgentToolSpec


def _dummy_handler(data: dict) -> str:
    return f"processed:{data.get('key', '')}"


def _make_tool(name: str = "test_tool", risk_level: str = "low") -> RegisteredTool:
    spec = AgentToolSpec(
        name=name,
        description=f"Tool {name}",
        risk_level=risk_level,
    )
    return RegisteredTool(spec=spec, handler=_dummy_handler)


class TestRegisteredTool:
    def test_accepts_callable_handler(self):
        tool = _make_tool()
        assert callable(tool.handler)

    def test_rejects_non_callable_handler(self):
        spec = AgentToolSpec(name="bad", description="desc", risk_level="low")
        with pytest.raises(TypeError, match="handler must be callable"):
            RegisteredTool(spec=spec, handler="not_callable")  # type: ignore[arg-type]

    def test_spec_is_accessible(self):
        tool = _make_tool("my_tool")
        assert tool.spec.name == "my_tool"
        assert tool.spec.description == "Tool my_tool"


class TestToolRegistry:
    def test_starts_empty(self):
        reg = ToolRegistry()
        assert reg.list_names() == []
        assert reg.list_specs() == []

    def test_register_adds_tool(self):
        reg = ToolRegistry()
        tool = _make_tool("greet")
        reg.register(tool)
        assert "greet" in reg.list_names()

    def test_has_returns_true_for_registered(self):
        reg = ToolRegistry()
        reg.register(_make_tool("greet"))
        assert reg.has("greet") is True

    def test_has_returns_false_for_unknown(self):
        reg = ToolRegistry()
        assert reg.has("nope") is False

    def test_get_returns_registered_tool(self):
        reg = ToolRegistry()
        reg.register(_make_tool("greet"))
        tool = reg.get("greet")
        assert tool.spec.name == "greet"
        assert callable(tool.handler)

    def test_get_unknown_raises_key_error(self):
        reg = ToolRegistry()
        with pytest.raises(KeyError, match="unknown tool: 'missing'"):
            reg.get("missing")

    def test_duplicate_registration_raises(self):
        reg = ToolRegistry()
        reg.register(_make_tool("dup"))
        with pytest.raises(ValueError, match="tool already registered: 'dup'"):
            reg.register(_make_tool("dup"))

    def test_list_names_deterministic_order(self):
        reg = ToolRegistry()
        reg.register(_make_tool("a"))
        reg.register(_make_tool("b"))
        reg.register(_make_tool("c"))
        assert reg.list_names() == ["a", "b", "c"]

    def test_list_specs_returns_spec_objects(self):
        reg = ToolRegistry()
        reg.register(_make_tool("t1"))
        reg.register(_make_tool("t2"))
        specs = reg.list_specs()
        assert len(specs) == 2
        assert all(isinstance(s, AgentToolSpec) for s in specs)
        assert [s.name for s in specs] == ["t1", "t2"]

    def test_call_invokes_handler_with_input(self):
        reg = ToolRegistry()
        reg.register(_make_tool("echo"))
        result = reg.call("echo", {"key": "hello"})
        assert result == "processed:hello"

    def test_call_returns_handler_result(self):
        reg = ToolRegistry()
        reg.register(_make_tool("add"))
        result = reg.call("add", {"key": "world"})
        assert result == "processed:world"

    def test_call_unknown_raises_key_error(self):
        reg = ToolRegistry()
        with pytest.raises(KeyError, match="unknown tool: 'nope'"):
            reg.call("nope", {})

    def test_spec_risk_level_preserved(self):
        reg = ToolRegistry()
        reg.register(_make_tool("risky", risk_level="high"))
        spec = reg.get("risky").spec
        assert spec.risk_level == "high"

    def test_multiple_tools_independent(self):
        reg = ToolRegistry()
        reg.register(_make_tool("a", risk_level="low"))
        reg.register(_make_tool("b", risk_level="medium"))
        reg.register(_make_tool("c", risk_level="high"))
        assert reg.list_names() == ["a", "b", "c"]
        assert reg.get("a").spec.risk_level == "low"
        assert reg.get("b").spec.risk_level == "medium"
        assert reg.get("c").spec.risk_level == "high"
