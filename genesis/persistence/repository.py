"""Transactional SQLite persistence for Genesis Alpha worlds."""
from __future__ import annotations
import json
import sqlite3
from dataclasses import asdict
from pathlib import Path
from typing import Any
from genesis.core.models import Agent, World, WorldEvent

SCHEMA_VERSION = 1

class PersistenceError(RuntimeError):
    """Raised when persisted Genesis state is invalid or unsupported."""

def _json_default(value: Any):
    raise TypeError(f"Value is not JSON serializable: {type(value).__name__}")

class WorldRepository:
    def __init__(self, database: str | Path):
        self.database = str(database)
        Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS schema_meta (singleton INTEGER PRIMARY KEY CHECK(singleton = 1), version INTEGER NOT NULL);
                INSERT OR IGNORE INTO schema_meta(singleton, version) VALUES (1, 1);
                CREATE TABLE IF NOT EXISTS world_snapshots (
                    snapshot_id INTEGER PRIMARY KEY AUTOINCREMENT, world_id TEXT NOT NULL,
                    schema_version INTEGER NOT NULL, world_tick INTEGER NOT NULL,
                    event_cursor INTEGER NOT NULL, payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE INDEX IF NOT EXISTS idx_snapshots_world ON world_snapshots(world_id, snapshot_id DESC);
                CREATE TABLE IF NOT EXISTS world_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT, event_id TEXT NOT NULL UNIQUE,
                    world_id TEXT NOT NULL, tick INTEGER NOT NULL, event_type TEXT NOT NULL,
                    actor_id TEXT, payload_json TEXT NOT NULL,
                    recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
                CREATE INDEX IF NOT EXISTS idx_events_world_sequence ON world_events(world_id, sequence);
                CREATE TABLE IF NOT EXISTS agent_runtime_cursors (
                    world_id TEXT NOT NULL, agent_id TEXT NOT NULL, last_event_id TEXT,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY(world_id, agent_id));
            """)
            version = db.execute("SELECT version FROM schema_meta WHERE singleton = 1").fetchone()[0]
            if version > SCHEMA_VERSION:
                raise PersistenceError(f"Database schema {version} is newer than supported {SCHEMA_VERSION}")
            if version < SCHEMA_VERSION:
                raise PersistenceError(f"No migration path from schema {version} to {SCHEMA_VERSION}")

    def _connect(self):
        db = sqlite3.connect(self.database, timeout=30)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        db.execute("PRAGMA busy_timeout = 30000")
        return db

    @staticmethod
    def _world_payload(world: World) -> dict:
        return {"world_id": world.world_id, "name": world.name, "tick": world.tick,
                "agents": [asdict(agent) for agent in world.agents.values()],
                "events": [asdict(event) for event in world.events]}

    def save(self, world: World) -> int:
        if not world.world_id or not world.name or world.tick < 0:
            raise PersistenceError("World identity, name, and non-negative tick are required")
        try:
            payload_json = json.dumps(self._world_payload(world), ensure_ascii=False, sort_keys=True, default=_json_default)
            with self._connect() as db:
                for event in world.events:
                    db.execute("""INSERT OR IGNORE INTO world_events
                        (event_id, world_id, tick, event_type, actor_id, payload_json)
                        VALUES (?, ?, ?, ?, ?, ?)""",
                        (event.event_id, world.world_id, event.tick, event.event_type, event.actor_id,
                         json.dumps(event.payload, ensure_ascii=False, sort_keys=True)))
                cursor = db.execute("SELECT COALESCE(MAX(sequence), 0) FROM world_events WHERE world_id = ?", (world.world_id,)).fetchone()[0]
                db.execute("""INSERT INTO world_snapshots
                    (world_id, schema_version, world_tick, event_cursor, payload_json)
                    VALUES (?, ?, ?, ?, ?)""", (world.world_id, SCHEMA_VERSION, world.tick, cursor, payload_json))
                snapshot_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
            return int(snapshot_id)
        except (TypeError, ValueError, sqlite3.Error) as exc:
            raise PersistenceError(f"Could not save world snapshot: {exc}") from exc

    def load(self, world_id: str) -> World:
        if not world_id:
            raise PersistenceError("world_id is required")
        with self._connect() as db:
            snapshot = db.execute("""SELECT * FROM world_snapshots WHERE world_id = ?
                ORDER BY snapshot_id DESC LIMIT 1""", (world_id,)).fetchone()
            if snapshot is None:
                raise KeyError(world_id)
            if snapshot["schema_version"] != SCHEMA_VERSION:
                raise PersistenceError(f"Unsupported snapshot schema {snapshot['schema_version']}")
            payload = json.loads(snapshot["payload_json"])
            later = db.execute("""SELECT event_id, tick, event_type, actor_id, payload_json
                FROM world_events WHERE world_id = ? AND sequence > ? ORDER BY sequence""",
                (world_id, snapshot["event_cursor"])).fetchall()
        try:
            agents = {item["agent_id"]: Agent(**item) for item in payload["agents"]}
            events = [WorldEvent(**item) for item in payload["events"]]
            events.extend(WorldEvent(event_id=row["event_id"], tick=row["tick"], event_type=row["event_type"],
                actor_id=row["actor_id"], payload=json.loads(row["payload_json"])) for row in later)
            return World(world_id=payload["world_id"], name=payload["name"], tick=payload["tick"], agents=agents, events=events)
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise PersistenceError(f"Stored world snapshot is invalid: {exc}") from exc

    def latest_snapshot_info(self, world_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute("""SELECT snapshot_id, schema_version, world_tick, event_cursor, created_at
                FROM world_snapshots WHERE world_id = ? ORDER BY snapshot_id DESC LIMIT 1""", (world_id,)).fetchone()
        return dict(row) if row else None

    def set_agent_cursor(self, world_id: str, agent_id: str, last_event_id: str | None) -> None:
        if not world_id or not agent_id:
            raise PersistenceError("world_id and agent_id are required")
        with self._connect() as db:
            db.execute("""INSERT INTO agent_runtime_cursors(world_id, agent_id, last_event_id)
                VALUES (?, ?, ?) ON CONFLICT(world_id, agent_id) DO UPDATE SET
                last_event_id = excluded.last_event_id, updated_at = CURRENT_TIMESTAMP""",
                (world_id, agent_id, last_event_id))

    def get_agent_cursor(self, world_id: str, agent_id: str) -> str | None:
        with self._connect() as db:
            row = db.execute("SELECT last_event_id FROM agent_runtime_cursors WHERE world_id = ? AND agent_id = ?", (world_id, agent_id)).fetchone()
        return row["last_event_id"] if row else None

    def list_events(self, world_id: str, after_sequence: int = 0, limit: int = 500) -> list[dict]:
        if after_sequence < 0 or limit < 1:
            raise ValueError("after_sequence must be non-negative and limit positive")
        with self._connect() as db:
            rows = db.execute("""SELECT sequence, event_id, tick, event_type, actor_id, payload_json, recorded_at
                FROM world_events WHERE world_id = ? AND sequence > ? ORDER BY sequence LIMIT ?""",
                (world_id, after_sequence, limit)).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            result.append(item)
        return result
