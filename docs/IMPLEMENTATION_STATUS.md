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
- [x] Cognitive Resource Manager prototype: tier limits, daily per-agent budgets, exact private-context cache, and usage ledger.
- [x] Initial automated tests for world, memory, inference, runtime, messaging, persistence, relationship boundaries, message-linked social outcomes, commitment lifecycle, and agent decision/negotiation tests.
- [x] Vision, architecture, roadmap, cost, and governance documents.
- [x] First collaboration experiment protocol.

## Still to implement
- [x] SQLite world snapshots, event history, and durable agent runtime cursors (schema v1; retention and migrations still pending).
- [x] Directional, world-scoped relationship profiles with append-only interaction history and bounded trust/familiarity scores (agent-facing permissions and automatic event integration remain pending).
- [x] Message-linked social outcomes with participant-only message lookup, directional relationship updates, and idempotent outcome recording (agent authentication and independently verified outcomes remain pending).
- [x] Commitment and cooperation prototype: proposals, assignee acceptance/decline, event-cursor-based completion verification, overdue state, and evidence-linked relationship credit (authenticated agent principals and independent event verification remain pending).
- [x] Explainable decision support for capabilities, resource snapshots, active workload, deadline pressure, and explicit deadline counterproposals (resource reservations and authenticated agent principals remain pending).
- [ ] Agent-facing knowledge permissions and explicit sharing workflow.
- [ ] Independent evidence verification tools and scientific replication pipeline.
- [ ] Provider/model routing, current rate-card management, concurrency-safe budget reservations, and monthly reporting.
- [ ] Experiment runner and reproducible scoring.
- [ ] Human-facing API/UI.
- [ ] Continuous integration workflow.
- [ ] End-to-end validation of the complete Alpha system.

## Validation note
The runtime policy included in this milestone is deterministic scaffolding, not an intelligent model. Tests have been authored but have not yet been executed in a local target environment. Do not treat this checklist as evidence that tests pass.
