import pytest

from genesis.core.bootstrap import create_seeded_world
from genesis.core.world import WorldError
from genesis.social.relationships import RelationshipStore


def make_world():
    return create_seeded_world("social-test")


def test_relationship_is_directional_and_persistent(tmp_path):
    world = make_world()
    store = RelationshipStore(tmp_path / "social.db")
    store.record_interaction(world, "ari", "bela", interaction_type="help",
                             summary="Bela shared a useful tool.", trust_delta=0.2,
                             cooperative=True)
    assert store.get_relationship(world.world_id, "ari", "bela")["trust"] == pytest.approx(0.2)
    assert store.get_relationship(world.world_id, "bela", "ari") is None
    assert store.get_relationship(world.world_id, "ari", "bela")["cooperation_count"] == 1
    assert len(store.history(world.world_id, "ari", "bela")) == 1


def test_scores_are_bounded_and_interactions_accumulate(tmp_path):
    world = make_world()
    store = RelationshipStore(tmp_path / "social.db")
    for _ in range(8):
        store.record_interaction(world, "ari", "bela", interaction_type="test",
                                 summary="Repeated positive interaction.", trust_delta=0.25)
    relation = store.get_relationship(world.world_id, "ari", "bela")
    assert relation["trust"] == 1.0
    assert relation["familiarity"] == pytest.approx(0.8)
    assert relation["interaction_count"] == 8


def test_world_and_pair_validation(tmp_path):
    world = make_world()
    store = RelationshipStore(tmp_path / "social.db")
    with pytest.raises(WorldError):
        store.record_interaction(world, "ari", "missing", interaction_type="x", summary="y")
    with pytest.raises(WorldError):
        store.record_interaction(world, "ari", "ari", interaction_type="x", summary="y")
    with pytest.raises(ValueError):
        store.record_interaction(world, "ari", "bela", interaction_type="x",
                                 summary="y", trust_delta=0.5)


def test_relationships_are_isolated_by_world(tmp_path):
    world = make_world()
    store = RelationshipStore(tmp_path / "social.db")
    store.record_interaction(world, "ari", "bela", interaction_type="meeting", summary="Met.")
    assert store.get_relationship("another-world", "ari", "bela") is None


def test_relationship_store_does_not_mutate_agent_identity_or_private_memory(tmp_path):
    world = make_world()
    before = (world.agents["ari"].name, list(world.agents["ari"].goals),
              dict(world.agents["ari"].beliefs))
    store = RelationshipStore(tmp_path / "social.db")
    store.record_interaction(world, "ari", "bela", interaction_type="disagreement",
                             summary="They disagreed about a route.", trust_delta=-0.1)
    after = (world.agents["ari"].name, list(world.agents["ari"].goals),
             dict(world.agents["ari"].beliefs))
    assert after == before
