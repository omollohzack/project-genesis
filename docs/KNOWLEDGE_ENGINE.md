# Genesis Knowledge Engine (Alpha)

## Design boundary
A knowledge claim is a proposition under evaluation, not an established fact. It is separate from private episodic memory and raw world events. The ledger is world-scoped; it does not grant agents access to one another's private memories.

## Records
- Claim: proposition, world, creator, type, status, timestamps.
- Evidence: contributor, source type/reference, independence group, support/refute stance, confidence, concise summary, timestamp.
- Review: reviewer, outcome, method, rationale, timestamp. Reviews are append-only and do not silently overwrite automatic evidence status.

## Automatic status policy
- proposed: fewer than two distinct source groups support or refute the proposition.
- corroborated: at least two distinct supporting source groups and no refuting source group.
- contested: at least one supporting and one refuting source group.
- refuted: at least two distinct refuting source groups and no supporting source group.

The independence_key is an explicit provenance assertion supplied by the caller. The store cannot prove that sources are truly independent. Two agents repeating the same report count as one source group. Confidence values are recorded, not averaged into a misleading certainty score. A corroborated status is not proof of truth.

## Alpha limitations
- No automatic web research, scientific verifier, or epistemic logic engine is included.
- Review decisions are audit records, not an access-control or governance system.
- Source references and summaries are recorded; source documents are not copied into this database.
- World-level claim visibility is a prototype boundary; production access policies need a dedicated authorization layer.
- SQLite is appropriate for the small Alpha prototype, not a claim of large-scale concurrency readiness.
