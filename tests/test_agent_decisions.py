import pytest

from genesis.core.bootstrap import create_alpha_world
from genesis.core.world import WorldError, record_agent_event
from genesis.social.commitments import CommitmentStore
from genesis.social.decision import AgentDecisionEngine, DecisionError


def setup(tmp_path):
    world = create_alpha_world()
    db = tmp_path / "decision.db"
    commitments = CommitmentStore(db)
    decisions = AgentDecisionEngine(db)
    return world, commitments, decisions


def proposal(world, store, **extra):
    payload = {
        "area": "north",
        "quality": "complete",
        "required_capabilities": ["survey"],
        "required_resources": {"energy": 2},
    }
    payload.update(extra.pop("expected_payload", {}))
    return store.propose(
        world, "ari", "cato",
        title="Survey the northern area",
        description="Map and report the northern area",
        required_event_type="map.area_surveyed",
        expected_payload=payload,
        deadline_tick=world.tick + 8,
    )


def test_feasible_task_gets_explainable_accept_recommendation(tmp_path):
    world, store, engine = setup(tmp_path)
    cid = proposal(world, store)
    engine.set_profile(world, "cato", capabilities=["survey", "navigation"],
                        resources={"energy": 5}, max_active_commitments=2)
    result = engine.evaluate(world, cid, "cato")
    assert result["recommendation"] == "accept"
    assert result["score"] > 0.8
    assert result["reasons"]


def test_missing_capability_or_resources_recommends_decline(tmp_path):
    world, store, engine = setup(tmp_path)
    cid = proposal(world, store)
    engine.set_profile(world, "cato", capabilities=["navigation"],
                        resources={"energy": 1}, max_active_commitments=2)
    result = engine.evaluate(world, cid, "cato")
    assert result["recommendation"] == "decline"
    assert any("Missing capabilities" in reason for reason in result["reasons"])
    assert any("Insufficient resources" in reason for reason in result["reasons"])


def test_capacity_limit_is_considered(tmp_path):
    world, store, engine = setup(tmp_path)
    engine.set_profile(world, "cato", capabilities=["survey"],
                        resources={"energy": 5}, max_active_commitments=1)
    first = proposal(world, store)
    store.respond(world, first, "cato", accept=True)
    second = proposal(world, store)
    result = engine.evaluate(world, second, "cato")
    assert result["recommendation"] == "decline"
    assert any("Capacity reached" in reason for reason in result["reasons"])


def test_no_profile_recommends_negotiation_not_silent_rejection(tmp_path):
    world, store, engine = setup(tmp_path)
    cid = proposal(world, store)
    result = engine.evaluate(world, cid, "cato")
    assert result["recommendation"] == "negotiate"
    assert "uncertain" in result["reasons"][0]


def test_evaluation_does_not_accept_commitment(tmp_path):
    world, store, engine = setup(tmp_path)
    cid = proposal(world, store)
    engine.set_profile(world, "cato", capabilities=["survey"],
                        resources={"energy": 5})
    engine.evaluate(world, cid, "cato")
    assert store.get(world.world_id, cid)["status"] == "offered"


def test_counterproposal_requires_assignee_and_original_proposer_responds(tmp_path):
    world, store, engine = setup(tmp_path)
    cid = proposal(world, store)
    with pytest.raises(WorldError):
        engine.counterpropose(world, cid, "ari",
                              revised_deadline_tick=world.tick + 12,
                              rationale="Need more time")
    counter_id = engine.counterpropose(
        world, cid, "cato", revised_deadline_tick=world.tick + 12,
        rationale="The survey requires an extra expedition."
    )
    with pytest.raises(WorldError):
        engine.respond_to_counterproposal(world, counter_id, "bela", accept=True)
    result = engine.respond_to_counterproposal(world, counter_id, "ari", accept=True)
    assert result["status"] == "accepted"
    assert "revised deadline" in result["next_step"]
    assert store.get(world.world_id, cid)["deadline_tick"] == world.tick + 12


def test_counterproposal_can_be_rejected_without_mutating_original(tmp_path):
    world, store, engine = setup(tmp_path)
    cid = proposal(world, store)
    counter_id = engine.counterpropose(
        world, cid, "cato", revised_deadline_tick=world.tick + 12,
        rationale="Need more time"
    )
    result = engine.respond_to_counterproposal(world, counter_id, "ari", accept=False)
    assert result["status"] == "rejected"
    assert store.get(world.world_id, cid)["status"] == "offered"


def test_completion_metadata_is_not_required_in_world_evidence(tmp_path):
    world, store, engine = setup(tmp_path)
    cid = proposal(world, store)
    engine.set_profile(world, "cato", capabilities=["survey"],
                        resources={"energy": 5})
    store.respond(world, cid, "cato", accept=True)
    record_agent_event(world, "cato", "map.area_surveyed",
                       {"area": "north", "quality": "complete", "commitment_id": cid})
    assert store.reconcile(world, cid)["status"] == "completed"


def test_invalid_profile_values_are_rejected(tmp_path):
    world, store, engine = setup(tmp_path)
    with pytest.raises(DecisionError):
        engine.set_profile(world, "cato", capabilities=["survey"],
                           resources={"energy": -1})
    with pytest.raises(DecisionError):
        engine.set_profile(world, "cato", capabilities=["survey"],
                           resources={}, max_active_commitments=-1)
