from genesis.agents.runtime import AgentRuntime
from genesis.core.bootstrap import create_alpha_world
from genesis.core.world import advance_tick
from genesis.memory.store import SQLiteMemoryStore
from genesis.persistence.repository import WorldRepository


def test_runtime_resumes_agent_cursor_after_restart(tmp_path):
    database = tmp_path / "genesis.db"
    world = create_alpha_world()
    advance_tick(world)
    repository = WorldRepository(database)
    memory = SQLiteMemoryStore(database)

    first_runtime = AgentRuntime(memory, world_repository=repository)
    first_action = first_runtime.step(world, "ari")
    assert first_action.action_type == "reflect"
    assert len(memory.list_for_agent("ari")) == 1

    restarted_runtime = AgentRuntime(memory, world_repository=WorldRepository(database))
    second_action = restarted_runtime.step(world, "ari")
    assert second_action.action_type == "wait"
    assert len(memory.list_for_agent("ari")) == 1
