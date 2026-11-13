import pytest

from genesis.core.bootstrap import create_alpha_world
from genesis.core.world import WorldError, record_agent_event
from genesis.social.commitments import CommitmentError, CommitmentStore


def setup_store(tmp_path):
    return create_alpha_world(), CommitmentStore(tmp_path / "commitments.db")


def propose(world, store, **overrides):
    values = dict(
        title="Map the northern area",
        description="Survey and record the northern area.",
        required_event_type="map.area_surveyed",
        expected_payload={"area": "north", "quality": "complete", "commitment_id": cid},
        deadline_tick=world.tick + 5,
    )
    values.update(overrides)
    return store.propose(world, "ari", "cato", **values)


def test_propose_accept_and_verify_completion_updates_relationship(tmp_path):
    world, store = setup_store(tmp_path)
    cid = propose(world, store)
    assert store.get(world.world_id, cid)["status"] == "offered"
    accepted = store.respond(world, cid, "cato", accept=True)
    assert accepted["status"] == "accepted"

    record_agent_event(world, "cato", "map.area_surveyed",
                       {"area": "north", "quality": "complete"})
    result = store.reconcile(world, cid)
    assert result["status"] == "completed"
    assert result["matched_event_id"] == world.events[-1].event_id
    from genesis.social.relationships import RelationshipStore
    relation = RelationshipStore(tmp_path / "commitments.db").get_relationship(
        world.world_id, "ari", "cato")
    assert relation["trust"] == pytest.approx(0.15)
    assert relation["cooperation_count"] == 1


def test_message_or_wrong_event_cannot_fulfil_commitment(tmp_path):
    world, store = setup_store(tmp_path)
    cid = propose(world, store)
    store.respond(world, cid, "cato", accept=True)
    record_agent_event(world, "cato", "map.area_surveyed",
                       {"area": "south", "quality": "complete", "commitment_id": cid})
    assert store.reconcile(world, cid)["status"] == "accepted"


def test_event_before_acceptance_does_not_count(tmp_path):
    world, store = setup_store(tmp_path)
    record_agent_event(world, "cato", "map.area_surveyed",
                       {"area": "north", "quality": "complete"})
    cid = propose(world, store)
    store.respond(world, cid, "cato", accept=True)
    assert store.reconcile(world, cid)["status"] == "accepted"


def test_only_assignee_can_accept_or_decline(tmp_path):
    world, store = setup_store(tmp_path)
    cid = propose(world, store)
    with pytest.raises(WorldError):
        store.respond(world, cid, "bela", accept=True)
    assert store.get(world.world_id, cid)["status"] == "offered"


def test_declined_commitment_cannot_be_completed(tmp_path):
    world, store = setup_store(tmp_path)
    cid = propose(world, store)
    store.respond(world, cid, "cato", accept=False)
    record_agent_event(world, "cato", "map.area_surveyed",
                       {"area": "north", "quality": "complete"})
    assert store.reconcile(world, cid)["status"] == "declined"


def test_overdue_is_not_automatically_labelled_broken_promise(tmp_path):
    world, store = setup_store(tmp_path)
    cid = propose(world, store, deadline_tick=world.tick + 1)
    store.respond(world, cid, "cato", accept=True)
    world.tick += 2
    result = store.reconcile(world, cid)
    assert result["status"] == "overdue"
    assert store.history(world.world_id, cid)[-1]["action"] == "overdue"


def test_repeated_reconciliation_does_not_duplicate_trust(tmp_path):
    world, store = setup_store(tmp_path)
    cid = propose(world, store)
    store.respond(world, cid, "cato", accept=True)
    record_agent_event(world, "cato", "map.area_surveyed",
                       {"area": "north", "quality": "complete"})
    first = store.reconcile(world, cid)
    second = store.reconcile(world, cid)
    assert first["status"] == second["status"] == "completed"
    from genesis.social.relationships import RelationshipStore
    relation = RelationshipStore(tmp_path / "commitments.db").get_relationship(
        world.world_id, "ari", "cato")
    assert relation["interaction_count"] == 1
