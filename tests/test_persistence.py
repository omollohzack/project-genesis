import pytest
from genesis.core.bootstrap import create_alpha_world
from genesis.core.world import advance_tick, record_agent_event
from genesis.persistence.repository import PersistenceError, WorldRepository

def test_save_and_load_restores_world_agents_and_events(tmp_path):
    repo = WorldRepository(tmp_path / "genesis.db")
    world = create_alpha_world()
    advance_tick(world)
    record_agent_event(world, "ari", "agent.discovered", {"idea": "pattern"})
    snapshot_id = repo.save(world)
    restored = repo.load(world.world_id)
    assert snapshot_id == 1
    assert restored.tick == world.tick and restored.name == world.name
    assert set(restored.agents) == set(world.agents)
    assert [e.event_id for e in restored.events] == [e.event_id for e in world.events]
    assert restored.events[-1].payload["idea"] == "pattern"

def test_latest_snapshot_restores_state_and_history(tmp_path):
    repo = WorldRepository(tmp_path / "genesis.db")
    world = create_alpha_world()
    advance_tick(world); repo.save(world)
    advance_tick(world); record_agent_event(world, "bela", "agent.built", {"item": "shelter"})
    repo.save(world)
    restored = repo.load(world.world_id)
    assert restored.tick == 2 and len(restored.events) == 3
    assert restored.events[-1].event_type == "agent.built"

def test_agent_cursor_survives_repository_restart(tmp_path):
    path = tmp_path / "genesis.db"
    WorldRepository(path).set_agent_cursor("genesis-alpha", "ari", "event-123")
    assert WorldRepository(path).get_agent_cursor("genesis-alpha", "ari") == "event-123"

def test_unknown_world_raises_key_error(tmp_path):
    with pytest.raises(KeyError):
        WorldRepository(tmp_path / "genesis.db").load("missing")

def test_non_json_payload_rejected_without_partial_snapshot(tmp_path):
    repo = WorldRepository(tmp_path / "genesis.db")
    world = create_alpha_world()
    world.agents["ari"].beliefs["bad"] = object()
    with pytest.raises(PersistenceError):
        repo.save(world)
    assert repo.latest_snapshot_info(world.world_id) is None

def test_event_log_deduplicates_repeated_saves(tmp_path):
    repo = WorldRepository(tmp_path / "genesis.db")
    world = create_alpha_world(); advance_tick(world)
    repo.save(world); repo.save(world)
    assert len(repo.list_events(world.world_id)) == 1
