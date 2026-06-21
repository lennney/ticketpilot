"""Unit tests for WorkingMemory and EpisodicMemory (Batch 3)."""

import pytest

from ticketpilot.agent.memory import EpisodicMemory, WorkingMemory


# ---------------------------------------------------------------------------
# WorkingMemory
# ---------------------------------------------------------------------------


class TestWorkingMemory:
    def test_rejects_empty_run_id(self):
        with pytest.raises(ValueError, match="run_id must not be empty"):
            WorkingMemory("")

    def test_rejects_whitespace_run_id(self):
        with pytest.raises(ValueError, match="run_id must not be empty"):
            WorkingMemory("   ")

    def test_set_and_get(self):
        wm = WorkingMemory("r1")
        wm.set("key1", "value1")
        assert wm.get("key1") == "value1"

    def test_get_default(self):
        wm = WorkingMemory("r1")
        assert wm.get("nonexistent") is None
        assert wm.get("nonexistent", 42) == 42

    def test_has(self):
        wm = WorkingMemory("r1")
        wm.set("a", 1)
        assert wm.has("a") is True
        assert wm.has("b") is False

    def test_rejects_empty_key(self):
        wm = WorkingMemory("r1")
        with pytest.raises(ValueError, match="key must not be empty"):
            wm.set("", "val")

    def test_rejects_whitespace_key(self):
        wm = WorkingMemory("r1")
        with pytest.raises(ValueError, match="key must not be empty"):
            wm.set("  ", "val")

    def test_snapshot_returns_dict(self):
        wm = WorkingMemory("r1")
        wm.set("x", 1)
        snap = wm.snapshot()
        assert snap == {"x": 1}

    def test_snapshot_is_copy(self):
        wm = WorkingMemory("r1")
        wm.set("x", [1, 2, 3])
        snap = wm.snapshot()
        snap["x"].append(4)
        assert wm.get("x") == [1, 2, 3]

    def test_clear_removes_values(self):
        wm = WorkingMemory("r1")
        wm.set("x", 1)
        wm.clear()
        assert wm.get("x") is None

    def test_instances_isolated(self):
        wm_a = WorkingMemory("a")
        wm_b = WorkingMemory("b")
        wm_a.set("key", "a_val")
        wm_b.set("key", "b_val")
        assert wm_a.get("key") == "a_val"
        assert wm_b.get("key") == "b_val"

    def test_overwrite_value(self):
        wm = WorkingMemory("r1")
        wm.set("x", 1)
        wm.set("x", 2)
        assert wm.get("x") == 2


# ---------------------------------------------------------------------------
# EpisodicMemory
# ---------------------------------------------------------------------------


class TestEpisodicMemory:
    def test_starts_empty(self):
        mem = EpisodicMemory()
        assert mem.count() == 0
        assert mem.get_all() == []

    def test_append_increases_count(self):
        mem = EpisodicMemory()
        mem.append({"event": "start"})
        assert mem.count() == 1

    def test_get_all_returns_records(self):
        mem = EpisodicMemory()
        mem.append({"event": "a"})
        mem.append({"event": "b"})
        assert len(mem.get_all()) == 2
        assert mem.get_all()[0]["event"] == "a"
        assert mem.get_all()[1]["event"] == "b"

    def test_get_all_returns_copy(self):
        mem = EpisodicMemory()
        mem.append({"items": [1]})
        records = mem.get_all()
        records[0]["items"].append(2)
        assert mem.get_all()[0]["items"] == [1]

    def test_append_stores_copy(self):
        mem = EpisodicMemory()
        original = {"key": "val", "nested": [1]}
        mem.append(original)
        original["key"] = "changed"
        original["nested"].append(2)
        stored = mem.get_all()[0]
        assert stored["key"] == "val"
        assert stored["nested"] == [1]

    def test_clear_resets(self):
        mem = EpisodicMemory()
        mem.append({"a": 1})
        mem.clear()
        assert mem.count() == 0

    def test_multiple_appends(self):
        mem = EpisodicMemory()
        for i in range(5):
            mem.append({"i": i})
        assert mem.count() == 5

    def test_no_update_method(self):
        mem = EpisodicMemory()
        assert not hasattr(mem, "update")

    def test_no_delete_method(self):
        mem = EpisodicMemory()
        assert not hasattr(mem, "delete")
