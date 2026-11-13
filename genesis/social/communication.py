"""SQLite direct messages with participant-scoped retrieval."""

import sqlite3
from pathlib import Path
from uuid import uuid4

from genesis.core.models import World
from genesis.core.world import WorldError


class CommunicationStore:
    def __init__(self, database: str | Path):
        self.database = str(database)
        with self._connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY, world_id TEXT NOT NULL,
                sender_id TEXT NOT NULL, recipient_id TEXT NOT NULL,
                tick INTEGER NOT NULL, content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )""")
            db.execute("CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(world_id, recipient_id, tick)")

    def _connect(self):
        return sqlite3.connect(self.database)

    def send(self, world: World, sender_id: str, recipient_id: str, content: str) -> str:
        if sender_id not in world.agents or recipient_id not in world.agents:
            raise WorldError("Both sender and recipient must belong to this world")
        if sender_id == recipient_id:
            raise WorldError("Direct messages must have distinct participants")
        if world.agents[sender_id].status != "active" or world.agents[recipient_id].status != "active":
            raise WorldError("Inactive agents cannot exchange messages")
        if not isinstance(content, str) or not content.strip():
            raise ValueError("Message content cannot be empty")
        message_id = str(uuid4())
        with self._connect() as db:
            db.execute("INSERT INTO messages (message_id, world_id, sender_id, recipient_id, tick, content) VALUES (?, ?, ?, ?, ?, ?)",
                       (message_id, world.world_id, sender_id, recipient_id, world.tick, content.strip()))
        return message_id

    def inbox(self, world_id: str, requesting_agent_id: str, limit: int = 100) -> list[dict]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connect() as db:
            rows = db.execute("""SELECT message_id, world_id, sender_id, recipient_id, tick, content, created_at
                FROM messages WHERE world_id = ? AND recipient_id = ?
                ORDER BY tick, created_at, message_id LIMIT ?""",
                (world_id, requesting_agent_id, limit)).fetchall()
        keys = ("message_id", "world_id", "sender_id", "recipient_id", "tick", "content", "created_at")
        return [dict(zip(keys, row)) for row in rows]

    def sent(self, world_id: str, requesting_agent_id: str, limit: int = 100) -> list[dict]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connect() as db:
            rows = db.execute("""SELECT message_id, world_id, sender_id, recipient_id, tick, content, created_at
                FROM messages WHERE world_id = ? AND sender_id = ?
                ORDER BY tick, created_at, message_id LIMIT ?""",
                (world_id, requesting_agent_id, limit)).fetchall()
        keys = ("message_id", "world_id", "sender_id", "recipient_id", "tick", "content", "created_at")
        return [dict(zip(keys, row)) for row in rows]

    def get_message(self, world_id: str, message_id: str, requesting_agent_id: str) -> dict | None:
        """Return a message only to one of its two participants."""
        with self._connect() as db:
            row = db.execute("""SELECT message_id, world_id, sender_id, recipient_id, tick, content, created_at
                FROM messages WHERE world_id = ? AND message_id = ?
                AND (sender_id = ? OR recipient_id = ?)""",
                (world_id, message_id, requesting_agent_id, requesting_agent_id)).fetchone()
        if row is None:
            return None
        keys = ("message_id", "world_id", "sender_id", "recipient_id", "tick", "content", "created_at")
        return dict(zip(keys, row))
