# Implementation Status

Last updated: 2026-11-13

## Implemented foundation
- [x] Public GitHub repository and Python package skeleton.
- [x] Five canonical Alpha inhabitants.
- [x] Deterministic world tick and event recording.
- [x] SQLite private memory store with owner-scoped reads.
- [x] Provider-independent inference protocol and deterministic stub.
- [x] Basic event-driven agent runtime with replaceable policy interface.
- [x] Runtime action allowlist and private episodic reflection.
- [x] SQLite direct messaging with sender/recipient-scoped retrieval.
- [x] World-scoped knowledge ledger for claims, evidence, source independence, and review records.
- [x] Conservative claim evaluation: proposed, corroborated, contested, or refuted.
- [x] Initial automated tests for world, memory, inference, runtime, and messaging.
- [x] Vision, architecture, roadmap, cost, and governance documents.
- [x] First collaboration experiment protocol.

## Still to implement
- [ ] Durable agent runtime cursors and world snapshots/migrations.
- [ ] Relationship model and social dynamics.
- [ ] Agent-facing knowledge permissions and explicit sharing workflow.
- [ ] Independent evidence verification tools and scientific replication pipeline.
- [ ] Inference router, token accounting, budgets, caching, and monthly reports.
- [ ] Experiment runner and reproducible scoring.
- [ ] Human-facing API/UI.
- [ ] Continuous integration workflow.
- [ ] End-to-end validation of the complete Alpha system.

## Validation note
The runtime policy included in this milestone is deterministic scaffolding, not an intelligent model. Tests have been authored but have not yet been executed in a local target environment. Do not treat this checklist as evidence that tests pass.
