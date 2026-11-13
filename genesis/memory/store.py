"""SQLite memory store with mandatory owner-scoped reads."""

import json
import sqlite3
from pathlib import Path
from uuid import uuid4


class MemoryAccessError(PermissionError):
    """Raised when a caller attempts cross-agent memory access."""


class SQLiteMemoryStore:
    def __init__(self, database: str | Path):
        self.database = str(database)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS memories (
                    memory_id TEXT PRIMARY KEY,
                    owner_agent_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    content TEXT NOT NULL,
                    provenance TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )"""
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_owner ON memories(owner_agent_id)"
            )

    def _connect(self):
        return sqlite3.connect(self.database)

    def add(self, owner_agent_id: str, category: str, content: str,
            provenance: str = "agent_observation") -> str:
        if not owner_agent_id or not category or not content:
            raise ValueError("owner_agent_id, category, and content are required")
        memory_id = str(uuid4())
        with self._connect() as connection:
            connection.execute(
                """INSERT INTO memories
                   (memory_id, owner_agent_id, category, content, provenance)
                   VALUES (?, ?, ?, ?, ?)""",
                (memory_id, owner_agent_id, category, content, provenance),
            )
        return memory_id

    def get(self, memory_id: str, requesting_agent_id: str) -> dict:
        with self._connect() as connection:
            row = connection.execute(
                """SELECT memory_id, owner_agent_id, category, content, provenance, created_at
                   FROM memories WHERE memory_id = ?""",
                (memory_id,),
            ).fetchone()
        if row is None:
            raise KeyError(memory_id)
        if row[1] != requesting_agent_id:
            raise MemoryAccessError("Agents may only retrieve their own private memories")
        return dict(zip(
            ("memory_id", "owner_agent_id", "category", "content", "provenance", "created_at"),
            row,
        ))

    def list_for_agent(self, requesting_agent_id: str, limit: int = 100) -> list[dict]:
        if limit < 1:
            raise ValueError("limit must be positive")
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT memory_id, owner_agent_id, category, content, provenance, created_at
                   FROM memories WHERE owner_agent_id = ?
                   ORDER BY created_at, memory_id LIMIT ?""",
                (requesting_agent_id, limit),
            ).fetchall()
        keys = ("memory_id", "owner_agent_id", "category", "content", "provenance", "created_at")
        return [dict(zip(keys, row)) for row in rows]
