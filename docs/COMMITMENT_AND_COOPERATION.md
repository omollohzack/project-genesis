# Commitment and Cooperation System

## Purpose

Commitments turn social intentions into bounded, inspectable tasks. An agent can propose a task to another inhabitant; the assignee may accept or decline. An accepted commitment is completed only when Genesis can match a subsequent world event to its declared completion condition.

## Lifecycle

`offered -> accepted -> completed`

Alternative terminal or unresolved states:
- `declined`: the assignee declined the proposal.
- `overdue`: the response or completion deadline passed without the required transition.

An overdue commitment is **not automatically labelled a broken promise**. The Alpha system does not infer intent, excuses, or fault from lateness alone.

## Completion evidence

A proposal specifies:
- proposer and assignee
- title and description
- required world event type
- expected payload fields
- deadline world tick

The assignee must accept before the deadline. The engine records the event-list cursor at acceptance, so older events cannot be reused as evidence. Completion requires a later event:
- authored by the assigned agent
- with the exact required event type
- with a `commitment_id` payload field matching this exact commitment
- with every expected payload field matching
- occurring no later than the deadline

Extra event payload fields are allowed. The event must exist in the supplied world's event history; a message or self-reported completion is insufficient.

## Relationship effects

When a commitment is verified as completed, the proposer’s directional relationship toward the assignee receives a +0.15 trust adjustment and one cooperation count. The change and completion record are committed in the same SQLite transaction. Reconciliation is idempotent: repeated checks do not award trust twice.

No negative trust adjustment is applied merely because a task becomes overdue. A later evidence/adjudication process may distinguish inability, changed circumstances, deliberate breach, and false reporting.

## API

Use `CommitmentStore(database_path)`:
- `propose(world, proposer_id, assignee_id, ...)`
- `respond(world, commitment_id, agent_id, accept=True|False)`
- `reconcile(world, commitment_id)`
- `get(world_id, commitment_id)`
- `list_for_agent(world_id, agent_id, statuses=None)`
- `history(world_id, commitment_id)`

The commitment, relationship, and interaction tables must reside in the same SQLite file for atomic completion updates.

## Limitations

This is a deterministic Alpha primitive, not yet an autonomous negotiation or project-management system. It does not model resources, subtasks, partial completion, delegation chains, dispute resolution, or independent verification of event producers. Authorization currently trusts the caller-supplied agent ID and world object; a production agent API must authenticate the runtime principal rather than accept arbitrary IDs. SQLite remains a single-host prototype.
