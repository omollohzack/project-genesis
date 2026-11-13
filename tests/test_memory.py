import pytest

from genesis.memory.store import MemoryAccessError, SQLiteMemoryStore


def test_memory_is_persisted_and_owner_scoped(tmp_path):
    store = SQLiteMemoryStore(tmp_path / "memory.sqlite3")
    memory_id = store.add("ari", "episodic", "I observed a river.", "environment")
    assert store.get(memory_id, "ari")["content"] == "I observed a river."
    with pytest.raises(MemoryAccessError):
        store.get(memory_id, "bela")
    assert store.list_for_agent("bela") == []
