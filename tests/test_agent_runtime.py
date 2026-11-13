import pytest

from genesis.agents.runtime import AgentAction, AgentRuntime
from genesis.core.bootstrap import create_alpha_world
from genesis.core.world import WorldError
from genesis.memory.store import SQLiteMemoryStore


class UnsafePolicy:
    def decide(self, agent, observation):
        return AgentAction("delete_world")


def test_runtime_records_private_reflection(tmp_path):
    world = create_alpha_world()
    memory = SQLiteMemoryStore(tmp_path / "memory.db")
    runtime = AgentRuntime(memory)
    runtime.step(world, "ari")
    # The initial seeded world has no events, so the deterministic policy waits.
    assert memory.list_for_agent("ari") == []


def test_runtime_reflects_on_world_event(tmp_path):
    from genesis.core.world import advance_tick
    world = create_alpha_world()
    advance_tick(world)
    memory = SQLiteMemoryStore(tmp_path / "memory.db")
    runtime = AgentRuntime(memory)
    action = runtime.step(world, "ari")
    assert action.action_type == "reflect"
    assert memory.list_for_agent("ari")[0]["provenance"] == "runtime_reflection"


def test_runtime_rejects_unsupported_action(tmp_path):
    runtime = AgentRuntime(SQLiteMemoryStore(tmp_path / "memory.db"), UnsafePolicy())
    with pytest.raises(WorldError):
        runtime.step(create_alpha_world(), "ari")
