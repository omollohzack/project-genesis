import pytest

from genesis.core.bootstrap import create_alpha_world
from genesis.core.world import WorldError
from genesis.social.communication import CommunicationStore


def test_direct_message_is_persisted_and_recipient_scoped(tmp_path):
    world = create_alpha_world()
    store = CommunicationStore(tmp_path / "social.db")
    message_id = store.send(world, "ari", "bela", "I found a useful pattern.")
    inbox = store.inbox(world.world_id, "bela")
    assert inbox[0]["message_id"] == message_id
    assert inbox[0]["content"] == "I found a useful pattern."
    assert store.inbox(world.world_id, "cato") == []
    assert store.sent(world.world_id, "ari")[0]["recipient_id"] == "bela"


def test_message_requires_valid_active_participants(tmp_path):
    world = create_alpha_world()
    store = CommunicationStore(tmp_path / "social.db")
    with pytest.raises(WorldError):
        store.send(world, "ari", "missing", "hello")
    with pytest.raises(ValueError):
        store.send(world, "ari", "bela", "  ")
