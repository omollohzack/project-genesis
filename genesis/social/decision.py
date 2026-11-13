"""Deterministic decision support and negotiation for Alpha commitments.

Recommendations are explainable and persisted, but never silently accept work.
Profiles are supplied by the simulation/controller; agent-facing authentication
must be added before exposing profile mutation to autonomous agents.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from genesis.core.models import World
from genesis.core.world import WorldError
from genesis.social.commitments import CommitmentStore, CommitmentError


class DecisionError(ValueError):
    """Raised when a decision or negotiation transition is invalid."""


class AgentDecisionEngine:
    def __init__(self, database: str | Path):
        self.database = str(database)
        self.commitments = CommitmentStore(database)
        with sqlite3.connect(self.database) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS agent_capacity_profiles (
                world_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                capabilities_json TEXT NOT NULL,
                resources_json TEXT NOT NULL,
                max_active_commitments INTEGER NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(world_id, agent_id)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS commitment_decisions (
                decision_id TEXT PRIMARY KEY,
                world_id TEXT NOT NULL,
                commitment_id TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                score REAL NOT NULL,
                reasons_json TEXT NOT NULL,
                created_tick INTEGER NOT NULL
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS counterproposals (
                counterproposal_id TEXT PRIMARY KEY,
                world_id TEXT NOT NULL,
                commitment_id TEXT NOT NULL,
                proposer_id TEXT NOT NULL,
                recipient_id TEXT NOT NULL,
                revised_deadline_tick INTEGER NOT NULL,
                rationale TEXT NOT NULL,
                status TEXT NOT NULL CHECK(status IN ('offered', 'accepted', 'rejected')),
                created_tick INTEGER NOT NULL,
                resolved_tick INTEGER
            )""")
            db.execute("""CREATE INDEX IF NOT EXISTS idx_counterproposal_recipient
                ON counterproposals(world_id, recipient_id, status)""")

    @staticmethod
    def _json_object(value, label):
        if not isinstance(value, dict):
            raise DecisionError(f"{label} must be a dictionary")
        try:
            return json.dumps(value, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise DecisionError(f"{label} must contain JSON-compatible values") from exc

    def set_profile(self, world: World, agent_id: str, *,
                    capabilities: list[str], resources: dict[str, float],
                    max_active_commitments: int = 2) -> None:
        if agent_id not in world.agents:
            raise WorldError(f"Unknown agent: {agent_id}")
        if world.agents[agent_id].status != "active":
            raise DecisionError("Only active agents can have an operational profile")
        if not isinstance(capabilities, list) or any(
            not isinstance(item, str) or not item.strip() for item in capabilities
        ):
            raise DecisionError("capabilities must be a list of non-empty strings")
        if isinstance(max_active_commitments, bool) or not isinstance(max_active_commitments, int) or max_active_commitments < 0:
            raise DecisionError("max_active_commitments must be a non-negative integer")
        if not isinstance(resources, dict):
            raise DecisionError("resources must be a dictionary")
        for name, amount in resources.items():
            if not isinstance(name, str) or not name.strip() or isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0:
                raise DecisionError("resource amounts must be non-negative numbers with named resources")
        capabilities_json = self._json_object({"items": sorted(set(capabilities))}, "capabilities")
        resources_json = self._json_object(resources, "resources")
        with sqlite3.connect(self.database) as db:
            db.execute("""INSERT INTO agent_capacity_profiles
                (world_id, agent_id, capabilities_json, resources_json, max_active_commitments)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(world_id, agent_id) DO UPDATE SET
                capabilities_json = excluded.capabilities_json,
                resources_json = excluded.resources_json,
                max_active_commitments = excluded.max_active_commitments,
                updated_at = CURRENT_TIMESTAMP""",
                (world.world_id, agent_id, capabilities_json, resources_json,
                 max_active_commitments))

    def profile(self, world_id: str, agent_id: str) -> dict | None:
        with sqlite3.connect(self.database) as db:
            row = db.execute("""SELECT capabilities_json, resources_json,
                max_active_commitments FROM agent_capacity_profiles
                WHERE world_id = ? AND agent_id = ?""", (world_id, agent_id)).fetchone()
        if row is None:
            return None
        return {"capabilities": json.loads(row[0])["items"],
                "resources": json.loads(row[1]),
                "max_active_commitments": row[2]}

    def evaluate(self, world: World, commitment_id: str, agent_id: str) -> dict:
        if agent_id not in world.agents or world.agents[agent_id].status != "active":
            raise WorldError("Only an active inhabitant can evaluate a commitment")
        commitment = self.commitments.get(world.world_id, commitment_id)
        if commitment is None:
            raise KeyError(commitment_id)
        if commitment["assignee_id"] != agent_id or commitment["status"] != "offered":
            raise DecisionError("Only the assigned inhabitant can evaluate an offered commitment")

        profile = self.profile(world.world_id, agent_id)
        reasons: list[str] = []
        score = 1.0
        recommendation = "accept"
        expected = commitment["expected_payload"]
        required_capabilities = expected.get("required_capabilities", [])
        required_resources = expected.get("required_resources", {})
        if not isinstance(required_capabilities, list) or not isinstance(required_resources, dict):
            raise DecisionError("Commitment capability/resource requirements have invalid shapes")

        if profile is None:
            reasons.append("No capability or resource profile is registered; feasibility is uncertain.")
            score -= 0.25
            recommendation = "negotiate"
            capabilities, resources, capacity = [], {}, None
        else:
            capabilities = profile["capabilities"]
            resources = profile["resources"]
            capacity = profile["max_active_commitments"]

        missing = sorted(set(required_capabilities) - set(capabilities))
        if missing:
            reasons.append("Missing capabilities: " + ", ".join(missing))
            score -= 0.65
            recommendation = "decline"

        insufficient = []
        for name, amount in required_resources.items():
            available = resources.get(name, 0)
            if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount < 0:
                raise DecisionError(f"Invalid required resource amount for {name}")
            if available < amount:
                insufficient.append(f"{name} ({available} available, {amount} required)")
        if insufficient:
            reasons.append("Insufficient resources: " + ", ".join(insufficient))
            score -= 0.45
            recommendation = "decline"

        active = self.commitments.list_for_agent(
            world.world_id, agent_id, statuses=("accepted",))
        if capacity is not None and len(active) >= capacity:
            reasons.append(f"Capacity reached: {len(active)} active commitments; limit is {capacity}.")
            score -= 0.5
            recommendation = "decline"

        remaining = commitment["deadline_tick"] - world.tick
        if remaining <= 1:
            reasons.append("Very little time remains before the deadline.")
            score -= 0.35
            if recommendation != "decline":
                recommendation = "negotiate"
        elif remaining <= 3:
            reasons.append("The deadline is relatively close.")
            score -= 0.15
            if recommendation == "accept":
                recommendation = "negotiate"

        agent_goals = " ".join(world.agents[agent_id].goals).lower()
        if any(term in agent_goals for term in commitment["title"].lower().split() if len(term) > 3):
            reasons.append("The task appears related to one or more stated goals.")
            score = min(1.0, score + 0.1)

        score = max(0.0, min(1.0, score))
        if not reasons:
            reasons.append("No configured capability, resource, capacity, or deadline blockers were found.")
        decision_id = str(uuid4())
        with sqlite3.connect(self.database) as db:
            db.execute("""INSERT INTO commitment_decisions
                (decision_id, world_id, commitment_id, agent_id, recommendation,
                 score, reasons_json, created_tick)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (decision_id, world.world_id, commitment_id, agent_id,
                 recommendation, score, json.dumps(reasons), world.tick))
        return {"decision_id": decision_id, "recommendation": recommendation,
                "score": score, "reasons": reasons}

    def decision_history(self, world_id: str, commitment_id: str) -> list[dict]:
        with sqlite3.connect(self.database) as db:
            rows = db.execute("""SELECT decision_id, agent_id, recommendation,
                score, reasons_json, created_tick FROM commitment_decisions
                WHERE world_id = ? AND commitment_id = ? ORDER BY rowid""",
                (world_id, commitment_id)).fetchall()
        return [{"decision_id": row[0], "agent_id": row[1],
                 "recommendation": row[2], "score": row[3],
                 "reasons": json.loads(row[4]), "created_tick": row[5]}
                for row in rows]

    def counterpropose(self, world: World, commitment_id: str, agent_id: str, *,
                       revised_deadline_tick: int, rationale: str) -> str:
        commitment = self.commitments.get(world.world_id, commitment_id)
        if commitment is None:
            raise KeyError(commitment_id)
        if agent_id != commitment["assignee_id"]:
            raise WorldError("Only the assigned inhabitant can counterpropose")
        if world.agents.get(agent_id) is None or world.agents[agent_id].status != "active":
            raise WorldError("Only an active inhabitant can counterpropose")
        if commitment["status"] != "offered":
            raise DecisionError("Only offered commitments can be counterproposed")
        if isinstance(revised_deadline_tick, bool) or not isinstance(revised_deadline_tick, int):
            raise DecisionError("revised_deadline_tick must be an integer")
        if revised_deadline_tick <= max(world.tick, commitment["deadline_tick"]):
            raise DecisionError("Counterproposal deadline must extend the original deadline")
        if not isinstance(rationale, str) or not rationale.strip():
            raise DecisionError("A counterproposal rationale is required")
        counter_id = str(uuid4())
        with sqlite3.connect(self.database) as db:
            db.execute("""INSERT INTO counterproposals
                (counterproposal_id, world_id, commitment_id, proposer_id, recipient_id,
                 revised_deadline_tick, rationale, status, created_tick)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'offered', ?)""",
                (counter_id, world.world_id, commitment_id, agent_id,
                 commitment["proposer_id"], revised_deadline_tick,
                 rationale.strip(), world.tick))
        return counter_id

    def respond_to_counterproposal(self, world: World, counterproposal_id: str,
                                   agent_id: str, *, accept: bool) -> dict:
        if not isinstance(accept, bool):
            raise DecisionError("accept must be a boolean")
        with sqlite3.connect(self.database, timeout=15) as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("""SELECT * FROM counterproposals
                WHERE counterproposal_id = ? AND world_id = ?""",
                (counterproposal_id, world.world_id)).fetchone()
            if row is None:
                raise KeyError(counterproposal_id)
            if row[4] != agent_id:
                raise WorldError("Only the original proposer can respond to a counterproposal")
            if row[7] != "offered":
                raise DecisionError("Counterproposal has already been resolved")
            status = "accepted" if accept else "rejected"
            db.execute("""UPDATE counterproposals SET status = ?, resolved_tick = ?
                WHERE counterproposal_id = ?""",
                (status, world.tick, counterproposal_id))
            return {"counterproposal_id": counterproposal_id,
                    "commitment_id": row[2], "status": status,
                    "revised_deadline_tick": row[5],
                    "rationale": row[6],
                    "next_step": ("Create a revised commitment using the agreed terms."
                                  if accept else "The original offer remains unchanged.")}

    def counterproposal_history(self, world_id: str, commitment_id: str) -> list[dict]:
        with sqlite3.connect(self.database) as db:
            rows = db.execute("""SELECT counterproposal_id, proposer_id, recipient_id,
                revised_deadline_tick, rationale, status, created_tick, resolved_tick
                FROM counterproposals WHERE world_id = ? AND commitment_id = ?
                ORDER BY rowid""", (world_id, commitment_id)).fetchall()
        keys = ("counterproposal_id", "proposer_id", "recipient_id",
                "revised_deadline_tick", "rationale", "status",
                "created_tick", "resolved_tick")
        return [dict(zip(keys, row)) for row in rows]
