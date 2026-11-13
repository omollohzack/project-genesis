import pytest

from genesis.core.bootstrap import create_alpha_world
from genesis.core.world import WorldError
from genesis.social.communication import CommunicationStore
from genesis.social.interactions import SocialInteractionEngine
from genesis.social.relationships import RelationshipStore


def setup_social(tmp_path):
    world = create_alpha_world()
    database = tmp_path / "social.db"
    messages = CommunicationStore(database)
    engine = SocialInteractionEngine(database)
    return world, messages, engine


def test_message_does_not_automatically_change_trust(tmp_path):
    world, messages, engine = setup_social(tmp_path)
    message_id = messages.send(world, "ari", "bela", "Would you help me test this idea?")
    assert engine.relationships.get_relationship(world.world_id, "ari", "bela") is None
    assert engine.record_outcome(world, message_id, "ari", outcome="neutral",
                                 summary="A request was sent.") is not None
    assert engine.relationships.get_relationship(world.world_id, "ari", "bela")["trust"] == 0.0


def test_cooperation_outcome_updates_only_observers_perspective(tmp_path):
    world, messages, engine = setup_social(tmp_path)
    message_id = messages.send(world, "ari", "bela", "Let's solve the puzzle together.")
    engine.record_outcome(world, message_id, "ari", outcome="cooperation",
                          summary="Bela worked through the puzzle with Ari.")
    ari_view = engine.relationships.get_relationship(world.world_id, "ari", "bela")
    assert ari_view["trust"] == pytest.approx(0.1)
    assert ari_view["cooperation_count"] == 1
    assert engine.relationships.get_relationship(world.world_id, "bela", "ari") is None


def test_outcome_is_idempotent_per_message_and_observer(tmp_path):
    world, messages, engine = setup_social(tmp_path)
    message_id = messages.send(world, "ari", "bela", "Can you help?")
    first = engine.record_outcome(world, message_id, "ari", outcome="helpful",
                                  summary="Help was provided.")
    second = engine.record_outcome(world, message_id, "ari", outcome="helpful",
                                   summary="Duplicate submission.")
    assert first == second
    relation = engine.relationships.get_relationship(world.world_id, "ari", "bela")
    assert relation["interaction_count"] == 1
    assert relation["trust"] == pytest.approx(0.1)


def test_both_participants_can_record_independent_perspectives(tmp_path):
    world, messages, engine = setup_social(tmp_path)
    message_id = messages.send(world, "ari", "bela", "I disagree with this plan.")
    engine.record_outcome(world, message_id, "ari", outcome="disagreement",
                          summary="Ari experienced a disagreement.")
    engine.record_outcome(world, message_id, "bela", outcome="neutral",
                          summary="Bela considered the exchange neutral.")
    assert engine.relationships.get_relationship(world.world_id, "ari", "bela")["trust"] == pytest.approx(-0.03)
    assert engine.relationships.get_relationship(world.world_id, "bela", "ari")["trust"] == 0.0


def test_non_participant_cannot_read_or_rate_message(tmp_path):
    world, messages, engine = setup_social(tmp_path)
    message_id = messages.send(world, "ari", "bela", "Private message.")
    assert messages.get_message(world.world_id, message_id, "cato") is None
    with pytest.raises(WorldError):
        engine.record_outcome(world, message_id, "cato", outcome="helpful",
                              summary="Unauthorized rating.")


def test_unknown_outcome_is_rejected(tmp_path):
    world, messages, engine = setup_social(tmp_path)
    message_id = messages.send(world, "ari", "bela", "Hello.")
    with pytest.raises(ValueError):
        engine.record_outcome(world, message_id, "ari", outcome="instant_soulmate",
                              summary="Unsupported category.")
