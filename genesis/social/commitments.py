"""Evidence-checked commitments between Genesis inhabitants.

A commitment is a proposal until accepted. Fulfilment is recognized only when
an accepted commitment matches an actual world event produced by its assignee.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from genesis.core.models import World
from genesis.core.world import WorldError


class CommitmentError(ValueError):
    """Raised when a commitment transition is invalid."""


class CommitmentStore:
    def __init__(self, database: str | Path):
        self.database = str(database)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS commitments (
                commitment_id TEXT PRIMARY KEY,
                world_id TEXT NOT NULL,
                proposer_id TEXT NOT NULL,
                assignee_id TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                required_event_type TEXT NOT NULL,
                expected_payload_json TEXT NOT NULL,
                created_tick INTEGER NOT NULL,
                deadline_tick INTEGER NOT NULL,
                accepted_tick INTEGER,
                status TEXT NOT NULL CHECK(status IN
                    ('offered', 'accepted', 'declined', 'completed', 'overdue')),
                matched_event_id TEXT,
                resolved_tick INTEGER
            )""")
            db.execute("""CREATE INDEX IF NOT EXISTS idx_commitments_assignee
                ON commitments(world_id, assignee_id, status, deadline_tick)""")
            db.execute("""CREATE TABLE IF NOT EXISTS commitment_history (
                history_id TEXT PRIMARY KEY,
                commitment_id TEXT NOT NULL,
                world_id TEXT NOT NULL,
                actor_id TEXT,
                action TEXT NOT NULL,
                tick INTEGER NOT NULL,
                detail TEXT NOT NULL
            )""")

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 15000")
        return db

    @staticmethod
    def _active_pair(world: World, proposer_id: str, assignee_id: str) -> None:
        if proposer_id not in world.agents or assignee_id not in world.agents:
            raise WorldError("Both commitment participants must belong to this world")
        if proposer_id == assignee_id:
            raise CommitmentError("A commitment must involve two distinct agents")
        if world.agents[proposer_id].status != "active" or world.agents[assignee_id].status != "active":
            raise CommitmentError("Both participants must be active")

    @staticmethod
    def _history(db, commitment_id: str, world_id: str, actor_id: str | None,
                 action: str, tick: int, detail: str) -> None:
        db.execute("""INSERT INTO commitment_history
            (history_id, commitment_id, world_id, actor_id, action, tick, detail)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (str(uuid4()), commitment_id, world_id, actor_id, action, tick, detail))

    def propose(
        self, world: World, proposer_id: str, assignee_id: str, *,
        title: str, description: str, required_event_type: str,
        expected_payload: dict | None = None, deadline_tick: int,
    ) -> str:
        self._active_pair(world, proposer_id, assignee_id)
        for value, label in ((title, "title"), (description, "description"),
                             (required_event_type, "required_event_type")):
            if not isinstance(value, str) or not value.strip():
                raise CommitmentError(f"{label} cannot be empty")
        if isinstance(deadline_tick, bool) or not isinstance(deadline_tick, int):
            raise CommitmentError("deadline_tick must be an integer")
        if deadline_tick <= world.tick:
            raise CommitmentError("deadline_tick must be later than the current world tick")
        if expected_payload is None:
            expected_payload = {}
        if not isinstance(expected_payload, dict):
            raise CommitmentError("expected_payload must be a dictionary")
        try:
            payload_json = json.dumps(expected_payload, sort_keys=True, separators=(",", ":"))
        except (TypeError, ValueError) as exc:
            raise CommitmentError("expected_payload must contain JSON-compatible values") from exc

        commitment_id = str(uuid4())
        with self._connect() as db:
            db.execute("""INSERT INTO commitments
                (commitment_id, world_id, proposer_id, assignee_id, title, description,
                 required_event_type, expected_payload_json, created_tick, deadline_tick, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'offered')""",
                (commitment_id, world.world_id, proposer_id, assignee_id, title.strip(),
                 description.strip(), required_event_type.strip(), payload_json,
                 world.tick, deadline_tick))
            self._history(db, commitment_id, world.world_id, proposer_id, "proposed",
                          world.tick, title.strip())
        return commitment_id

    def respond(self, world: World, commitment_id: str, agent_id: str, *,
                accept: bool) -> dict:
        if not isinstance(accept, bool):
            raise CommitmentError("accept must be a boolean")
        if agent_id not in world.agents or world.agents[agent_id].status != "active":
            raise WorldError("Only an active inhabitant can respond")
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM commitments WHERE commitment_id = ? AND world_id = ?",
                             (commitment_id, world.world_id)).fetchone()
            if row is None:
                raise KeyError(commitment_id)
            if row["assignee_id"] != agent_id:
                raise WorldError("Only the assigned inhabitant can respond")
            if row["status"] != "offered":
                raise CommitmentError("Only an offered commitment can be accepted or declined")
            if world.tick > row["deadline_tick"]:
                db.execute("UPDATE commitments SET status = 'overdue', resolved_tick = ? WHERE commitment_id = ?",
                           (world.tick, commitment_id))
                self._history(db, commitment_id, world.world_id, None, "overdue",
                              world.tick, "Response deadline passed")
                raise CommitmentError("The response deadline has passed")
            status = "accepted" if accept else "declined"
            accepted_tick = world.tick if accept else None
            db.execute("UPDATE commitments SET status = ?, accepted_tick = ?, resolved_tick = ? WHERE commitment_id = ?",
                       (status, accepted_tick, None if accept else world.tick, commitment_id))
            self._history(db, commitment_id, world.world_id, agent_id, status,
                          world.tick, "Assignee response")
            updated = db.execute("SELECT * FROM commitments WHERE commitment_id = ?",
                                  (commitment_id,)).fetchone()
            return dict(updated)

    @staticmethod
    def _matches(event, required_event_type: str, expected_payload: dict) -> bool:
        if event.event_type != required_event_type or event.actor_id is None:
            return False
        return all(event.payload.get(key) == value for key, value in expected_payload.items())

    def reconcile(self, world: World, commitment_id: str) -> dict:
        """Match accepted work to assignee-authored world events.

        A completion event must occur after acceptance and no later than the
        deadline. Merely claiming completion in a message is not sufficient.
        """
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM commitments WHERE commitment_id = ? AND world_id = ?",
                             (commitment_id, world.world_id)).fetchone()
            if row is None:
                raise KeyError(commitment_id)
            if row["status"] in ("completed", "declined", "overdue"):
                return dict(row)
            if row["status"] != "accepted":
                raise CommitmentError("Only accepted commitments can be reconciled")

            expected = json.loads(row["expected_payload_json"])
            match = next((event for event in world.events
                          if event.actor_id == row["assignee_id"]
                          and event.tick >= row["accepted_tick"]
                          and event.tick <= row["deadline_tick"]
                          and self._matches(event, row["required_event_type"], expected)), None)
            if match is not None:
                db.execute("""UPDATE commitments SET status = 'completed',
                    matched_event_id = ?, resolved_tick = ? WHERE commitment_id = ?""",
                    (match.event_id, world.tick, commitment_id))
                self._history(db, commitment_id, world.world_id, row["assignee_id"],
                              "completed", world.tick, f"Matched world event {match.event_id}")
                # The completion evidence and derived relationship update use
                # this same DB transaction to avoid partial credit.
                db.execute("""INSERT INTO relationship_events
                    (event_id, world_id, observer_id, target_id, tick, interaction_type,
                     summary, trust_delta, cooperative)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)""",
                    (str(uuid4()), world.world_id, row["proposer_id"], row["assignee_id"],
                     world.tick, "commitment_fulfilled",
                     f"Commitment {commitment_id} matched world event {match.event_id}", 0.15))
                db.execute("""INSERT INTO relationships
                    (world_id, observer_id, target_id, trust, familiarity,
                     cooperation_count, interaction_count, last_interaction_tick)
                    VALUES (?, ?, ?, 0.15, 0.1, 1, 1, ?)
                    ON CONFLICT(world_id, observer_id, target_id) DO UPDATE SET
                        trust = MAX(-1.0, MIN(1.0, relationships.trust + 0.15)),
                        familiarity = MIN(1.0, relationships.familiarity + 0.1),
                        cooperation_count = relationships.cooperation_count + 1,
                        interaction_count = relationships.interaction_count + 1,
                        last_interaction_tick = excluded.last_interaction_tick""",
                    (world.world_id, row["proposer_id"], row["assignee_id"], world.tick))
            elif world.tick > row["deadline_tick"]:
                db.execute("UPDATE commitments SET status = 'overdue', resolved_tick = ? WHERE commitment_id = ?",
                           (world.tick, commitment_id))
                self._history(db, commitment_id, world.world_id, None, "overdue",
                              world.tick, "No matching completion event before deadline")
            updated = db.execute("SELECT * FROM commitments WHERE commitment_id = ?",
                                  (commitment_id,)).fetchone()
            return dict(updated)

    def get(self, world_id: str, commitment_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("SELECT * FROM commitments WHERE world_id = ? AND commitment_id = ?",
                             (world_id, commitment_id)).fetchone()
        if row is None:
            return None
        result = dict(row)
        result["expected_payload"] = json.loads(result.pop("expected_payload_json"))
        return result

    def list_for_agent(self, world_id: str, agent_id: str,
                       statuses: tuple[str, ...] | None = None) -> list[dict]:
        query = "SELECT * FROM commitments WHERE world_id = ? AND (proposer_id = ? OR assignee_id = ?)"
        params: list = [world_id, agent_id, agent_id]
        if statuses:
            allowed = {"offered", "accepted", "declined", "completed", "overdue"}
            if not set(statuses).issubset(allowed):
                raise CommitmentError("Unknown commitment status filter")
            query += " AND status IN (" + ",".join("?" for _ in statuses) + ")"
            params.extend(statuses)
        query += " ORDER BY created_tick, commitment_id"
        with self._connect() as db:
            rows = db.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def history(self, world_id: str, commitment_id: str) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("""SELECT action, actor_id, tick, detail FROM commitment_history
                WHERE world_id = ? AND commitment_id = ? ORDER BY rowid""",
                (world_id, commitment_id)).fetchall()
        return [dict(row) for row in rows]
