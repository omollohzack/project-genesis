"""Directional, evidence-linked social relationships for agents."""

import sqlite3
from pathlib import Path
from uuid import uuid4

from genesis.core.models import World
from genesis.core.world import WorldError


class RelationshipStore:
    """Store what one agent's relationship to another looks like.

    Trust is directional: A's trust in B need not equal B's trust in A.
    Relationship scores are derived from recorded interactions, never direct
    edits to either participant's identity or private memory.
    """

    def __init__(self, database: str | Path):
        self.database = str(database)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS relationships (
                world_id TEXT NOT NULL,
                observer_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                trust REAL NOT NULL DEFAULT 0.0 CHECK(trust >= -1.0 AND trust <= 1.0),
                familiarity REAL NOT NULL DEFAULT 0.0 CHECK(familiarity >= 0.0 AND familiarity <= 1.0),
                cooperation_count INTEGER NOT NULL DEFAULT 0 CHECK(cooperation_count >= 0),
                interaction_count INTEGER NOT NULL DEFAULT 0 CHECK(interaction_count >= 0),
                last_interaction_tick INTEGER NOT NULL,
                PRIMARY KEY(world_id, observer_id, target_id),
                CHECK(observer_id != target_id)
            )""")
            db.execute("""CREATE TABLE IF NOT EXISTS relationship_events (
                event_id TEXT PRIMARY KEY,
                world_id TEXT NOT NULL,
                observer_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                tick INTEGER NOT NULL,
                interaction_type TEXT NOT NULL,
                summary TEXT NOT NULL,
                trust_delta REAL NOT NULL,
                cooperative INTEGER NOT NULL CHECK(cooperative IN (0, 1))
            )""")
            db.execute("""CREATE INDEX IF NOT EXISTS idx_relationship_events_pair
                ON relationship_events(world_id, observer_id, target_id, tick)""")

    def _connect(self):
        return sqlite3.connect(self.database)

    @staticmethod
    def _validate_pair(world: World, observer_id: str, target_id: str) -> None:
        if observer_id not in world.agents or target_id not in world.agents:
            raise WorldError("Both relationship participants must belong to this world")
        if observer_id == target_id:
            raise WorldError("An agent cannot form a relationship with itself")

    def record_interaction(
        self, world: World, observer_id: str, target_id: str, *,
        interaction_type: str, summary: str, trust_delta: float = 0.0,
        cooperative: bool = False,
    ) -> str:
        self._validate_pair(world, observer_id, target_id)
        if not isinstance(interaction_type, str) or not interaction_type.strip():
            raise ValueError("interaction_type cannot be empty")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("summary cannot be empty")
        if isinstance(trust_delta, bool) or not isinstance(trust_delta, (int, float)):
            raise ValueError("trust_delta must be numeric")
        if not -0.25 <= trust_delta <= 0.25:
            raise ValueError("trust_delta must be between -0.25 and 0.25")
        if not isinstance(cooperative, bool):
            raise ValueError("cooperative must be a boolean")

        event_id = str(uuid4())
        with self._connect() as db:
            db.execute("""INSERT INTO relationship_events
                (event_id, world_id, observer_id, target_id, tick, interaction_type,
                 summary, trust_delta, cooperative)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, world.world_id, observer_id, target_id, world.tick,
                 interaction_type.strip(), summary.strip(), float(trust_delta), int(cooperative)))
            db.execute("""INSERT INTO relationships
                (world_id, observer_id, target_id, trust, familiarity,
                 cooperation_count, interaction_count, last_interaction_tick)
                VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                ON CONFLICT(world_id, observer_id, target_id) DO UPDATE SET
                    trust = MAX(-1.0, MIN(1.0, relationships.trust + excluded.trust)),
                    familiarity = MIN(1.0, relationships.familiarity + 0.1),
                    cooperation_count = relationships.cooperation_count + excluded.cooperation_count,
                    interaction_count = relationships.interaction_count + 1,
                    last_interaction_tick = excluded.last_interaction_tick""",
                (world.world_id, observer_id, target_id, float(trust_delta), 0.1,
                 int(cooperative), world.tick))
        return event_id

    def get_relationship(self, world_id: str, observer_id: str, target_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("""SELECT world_id, observer_id, target_id, trust, familiarity,
                cooperation_count, interaction_count, last_interaction_tick
                FROM relationships WHERE world_id = ? AND observer_id = ? AND target_id = ?""",
                (world_id, observer_id, target_id)).fetchone()
        if row is None:
            return None
        keys = ("world_id", "observer_id", "target_id", "trust", "familiarity",
                "cooperation_count", "interaction_count", "last_interaction_tick")
        return dict(zip(keys, row))

    def list_relationships(self, world_id: str, observer_id: str) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("""SELECT world_id, observer_id, target_id, trust, familiarity,
                cooperation_count, interaction_count, last_interaction_tick
                FROM relationships WHERE world_id = ? AND observer_id = ?
                ORDER BY target_id""", (world_id, observer_id)).fetchall()
        keys = ("world_id", "observer_id", "target_id", "trust", "familiarity",
                "cooperation_count", "interaction_count", "last_interaction_tick")
        return [dict(zip(keys, row)) for row in rows]

    def history(self, world_id: str, observer_id: str, target_id: str) -> list[dict]:
        with self._connect() as db:
            rows = db.execute("""SELECT event_id, tick, interaction_type, summary,
                trust_delta, cooperative FROM relationship_events
                WHERE world_id = ? AND observer_id = ? AND target_id = ?
                ORDER BY tick, rowid""", (world_id, observer_id, target_id)).fetchall()
        keys = ("event_id", "tick", "interaction_type", "summary", "trust_delta", "cooperative")
        return [dict(zip(keys, row)) for row in rows]
