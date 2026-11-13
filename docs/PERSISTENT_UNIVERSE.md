# Persistent Universe (Alpha)

## Purpose
Preserve a world across process restarts: tick, inhabitants, agent attributes, event history, and per-agent runtime cursors.

## Storage design
- SQLite stores versioned world snapshots, an append-only event ledger, and runtime cursors.
- A save writes unseen event IDs and a complete world snapshot in one transaction.
- Loading restores the latest snapshot and appends event-ledger entries after its sequence cursor.
- Event IDs are unique, making repeated saves idempotent for the event ledger.
- Snapshot schema version is explicit. Unknown newer schemas and missing migration paths fail closed.

## Recovery contract
Call WorldRepository.save(world) at controlled checkpoint boundaries. On startup, call WorldRepository.load(world_id) and pass the restored world to the simulation. The repository does not silently create a new world if the requested world is missing.

Agent event cursors are stored independently using set_agent_cursor and get_agent_cursor. They are not yet automatically wired into every runtime; that integration is a follow-on step.

## Alpha limitations
- SQLite is a single-host prototype, not a distributed database or multi-host coordination mechanism.
- Snapshot retention/compaction and explicit migration scripts are not yet implemented.
- Backups and recovery from disk corruption require operational procedures.
- Persistence is not proof of uninterrupted execution or autonomous continuity.
