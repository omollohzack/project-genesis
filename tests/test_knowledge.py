import pytest
from genesis.knowledge.store import KnowledgeError, KnowledgeStore


def make_claim(store):
    return store.create_claim("genesis-alpha", "ari", "Water flows downhill.", "hypothesis")


def add(store, claim, source, stance="supports", agent="ari"):
    return store.add_evidence(claim, agent, "observation", source, source, stance, 0.9, f"Evidence from {source}")


def test_claim_starts_proposed_and_needs_independent_support(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.db")
    claim = make_claim(store)
    assert store.evaluate_claim(claim)["status"] == "proposed"
    add(store, claim, "field-note-1")
    assert store.evaluate_claim(claim)["status"] == "proposed"
    add(store, claim, "field-note-2", agent="bela")
    result = store.evaluate_claim(claim)
    assert result["status"] == "corroborated"
    assert result["independent_supporting_sources"] == 2
    assert "not proof" in result["interpretation"]


def test_duplicate_source_does_not_count_as_independent(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.db")
    claim = make_claim(store)
    add(store, claim, "same-report", agent="ari")
    add(store, claim, "same-report", agent="bela")
    assert store.evaluate_claim(claim)["status"] == "proposed"


def test_conflicting_evidence_marks_claim_contested(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.db")
    claim = make_claim(store)
    add(store, claim, "report-a", "supports")
    add(store, claim, "report-b", "refutes", agent="bela")
    assert store.evaluate_claim(claim)["status"] == "contested"


def test_two_independent_refutations_mark_claim_refuted(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.db")
    claim = make_claim(store)
    add(store, claim, "test-a", "refutes")
    add(store, claim, "test-b", "refutes", agent="bela")
    assert store.evaluate_claim(claim)["status"] == "refuted"


def test_review_is_a_separate_auditable_record(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.db")
    claim = make_claim(store)
    review_id = store.add_review(claim, "human-reviewer", "inconclusive", "replication", "More trials needed")
    result = store.get_claim(claim)
    assert result["reviews"][0]["review_id"] == review_id
    assert result["claim"]["status"] == "proposed"


def test_invalid_confidence_and_missing_claim_are_rejected(tmp_path):
    store = KnowledgeStore(tmp_path / "knowledge.db")
    claim = make_claim(store)
    with pytest.raises(KnowledgeError):
        store.add_evidence(claim, "ari", "observation", "x", "x", "supports", 1.2, "bad")
    with pytest.raises(KeyError):
        store.add_evidence("missing", "ari", "observation", "x", "x", "supports", 0.8, "bad")
