"""Acceptance tests derived from the master specification (v0.2).

Each test maps to an acceptance criterion stated in the spec's milestones
(section 16) or its definition of Genesis Alpha success (section 19), rather
than to implementation details.
"""

import pytest

from genesis.core.bootstrap import create_alpha_world
from genesis.core.world import record_agent_event
from genesis.memory.store import MemoryAccessError, SQLiteMemoryStore
from genesis.persistence.repository import WorldRepository


def _agent_signature(world):
    return sorted(
        (a.agent_id, a.name, a.role, tuple(a.goals), a.status)
        for a in world.agents.values()
    )


def test_world_state_survives_restart(tmp_path):
    """Spec milestones 1 and 3: stop and restart without losing world state."""
    database = tmp_path / "world.db"
    world = create_alpha_world()
    world.tick = 3
    record_agent_event(world, "cato", "map.area_surveyed", {"area": "north"})
    WorldRepository(database).save(world)

    memory_db = tmp_path / "memory.db"
    memory_id = SQLiteMemoryStore(memory_db).add(
        "cato", "episodic", "I surveyed the northern area.")

    # A restart means fresh store/repository objects over the same files.
    restored = WorldRepository(database).load(world.world_id)
    assert restored.tick == 3
    assert _agent_signature(restored) == _agent_signature(world)
    assert [(e.event_type, e.actor_id, e.payload) for e in restored.events] == [
        ("map.area_surveyed", "cato", {"area": "north"})]
    reopened = SQLiteMemoryStore(memory_db)
    assert reopened.get(memory_id, "cato")["content"] == \
        "I surveyed the northern area."


def test_private_memories_cannot_be_read_by_another_agent(tmp_path):
    """Spec milestone 3 and section 19: memories are isolated per agent."""
    store = SQLiteMemoryStore(tmp_path / "memory.db")
    memory_id = store.add("ari", "episodic", "Ari's private observation.")
    store.add("bela", "episodic", "Bela's private observation.")

    with pytest.raises(MemoryAccessError):
        store.get(memory_id, "bela")
    assert all(m["owner_agent_id"] == "bela" for m in store.list_for_agent("bela"))
    assert store.get(memory_id, "ari")["content"] == "Ari's private observation."


def test_alpha_world_bootstrap_is_reproducible():
    """Spec section 10: preserve initial states so experiments can replay.

    Two independently constructed Alpha worlds must start identical, and
    mutating one must not leak into the other.
    """
    first, second = create_alpha_world(), create_alpha_world()
    assert first.tick == second.tick == 0
    assert first.events == second.events == []
    assert _agent_signature(first) == _agent_signature(second)

    first.agents["ari"].goals.append("mutated goal")
    assert "mutated goal" not in second.agents["ari"].goals
