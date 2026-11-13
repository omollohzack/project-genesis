"""Outcome-driven relationship updates linked to addressed messages.

Messages alone do not change trust. A participant must explicitly record a
bounded, typed outcome. The outcome catalog, not a model-generated score,
determines the relationship adjustment.
"""

import sqlite3
from pathlib import Path
from uuid import uuid4

from genesis.core.models import World
from genesis.core.world import WorldError
from genesis.social.communication import CommunicationStore
from genesis.social.relationships import RelationshipStore


class SocialInteractionEngine:
    OUTCOMES = {
        "neutral": (0.0, False),
        "helpful": (0.10, True),
        "cooperation": (0.10, True),
        "commitment_fulfilled": (0.15, True),
        "disagreement": (-0.03, False),
        "conflict": (-0.10, False),
        "commitment_broken": (-0.20, False),
    }

    def __init__(self, database: str | Path):
        self.database = str(database)
        self.messages = CommunicationStore(database)
        self.relationships = RelationshipStore(database)
        with sqlite3.connect(self.database) as db:
            db.execute("""CREATE TABLE IF NOT EXISTS interaction_outcomes (
                message_id TEXT NOT NULL,
                observer_id TEXT NOT NULL,
                event_id TEXT NOT NULL UNIQUE,
                outcome TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(message_id, observer_id)
            )""")

    def record_outcome(
        self, world: World, message_id: str, observer_id: str, *,
        outcome: str, summary: str,
    ) -> str:
        """Record one participant's view of a message-related interaction.

        The same participant can record an outcome for a message only once.
        The other participant may record a different, independent perspective.
        """
        if observer_id not in world.agents:
            raise WorldError(f"Unknown observer: {observer_id}")
        if world.agents[observer_id].status != "active":
            raise WorldError("Inactive agents cannot record social outcomes")
        if outcome not in self.OUTCOMES:
            raise ValueError(f"Unsupported outcome: {outcome}")
        if not isinstance(summary, str) or not summary.strip():
            raise ValueError("summary cannot be empty")

        message = self.messages.get_message(world.world_id, message_id, observer_id)
        if message is None:
            raise WorldError("Message not found or observer is not a participant")
        target_id = (message["recipient_id"] if message["sender_id"] == observer_id
                     else message["sender_id"])
        trust_delta, cooperative = self.OUTCOMES[outcome]
        event_id = str(uuid4())

        # All writes share one SQLite transaction: outcome, evidence history,
        # and derived relationship cannot be partially updated.
        with sqlite3.connect(self.database, timeout=10) as db:
            db.execute("BEGIN IMMEDIATE")
            existing = db.execute(
                "SELECT event_id FROM interaction_outcomes WHERE message_id = ? AND observer_id = ?",
                (message_id, observer_id),
            ).fetchone()
            if existing:
                db.rollback()
                return existing[0]

            db.execute("""INSERT INTO interaction_outcomes
                (message_id, observer_id, event_id, outcome)
                VALUES (?, ?, ?, ?)""", (message_id, observer_id, event_id, outcome))
            db.execute("""INSERT INTO relationship_events
                (event_id, world_id, observer_id, target_id, tick, interaction_type,
                 summary, trust_delta, cooperative)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_id, world.world_id, observer_id, target_id, world.tick,
                 outcome, summary.strip(), trust_delta, int(cooperative)))
            db.execute("""INSERT INTO relationships
                (world_id, observer_id, target_id, trust, familiarity,
                 cooperation_count, interaction_count, last_interaction_tick)
                VALUES (?, ?, ?, ?, 0.1, ?, 1, ?)
                ON CONFLICT(world_id, observer_id, target_id) DO UPDATE SET
                    trust = MAX(-1.0, MIN(1.0, relationships.trust + excluded.trust)),
                    familiarity = MIN(1.0, relationships.familiarity + 0.1),
                    cooperation_count = relationships.cooperation_count + excluded.cooperation_count,
                    interaction_count = relationships.interaction_count + 1,
                    last_interaction_tick = excluded.last_interaction_tick""",
                (world.world_id, observer_id, target_id, trust_delta,
                 int(cooperative), world.tick))
        return event_id
