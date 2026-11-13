# Relationships and Social Dynamics

## Alpha scope

The relationship store records one agent's relationship to another. It is deliberately **directional**: Ari's trust in Bela can differ from Bela's trust in Ari. Relationships are scoped to a world and stored separately from agent identity and private memory.

Each recorded interaction appends a history entry and updates a derived profile:
- trust: bounded from -1.0 (strong distrust) to +1.0 (strong trust)
- familiarity: bounded from 0.0 to 1.0, increasing by 0.1 per recorded interaction
- cooperation count
- total interaction count
- last interaction tick

Trust updates are bounded to an absolute delta of 0.25 per interaction and cumulative trust is clamped to [-1, +1]. These values are simulation signals, not objective measurements of an agent's inner state.

## API

Use `RelationshipStore(database_path)`:
- `record_interaction(world, observer_id, target_id, interaction_type=..., summary=..., trust_delta=..., cooperative=...)`
- `get_relationship(world_id, observer_id, target_id)`
- `list_relationships(world_id, observer_id)`
- `history(world_id, observer_id, target_id)`

Only agents present in the supplied world can participate. Self-relationships, empty summaries, and out-of-range trust changes are rejected. The store does not mutate either agent's identity, goals, beliefs, or private memory. A future agent-facing API must authenticate the requesting agent before exposing private relationship history.

## Limitations and next steps

This is a persistence primitive, not yet a complete social simulation. It does not infer trust automatically from message sentiment, arbitrate disputes, or grant agents unrestricted access to relationship records. Interaction summaries are caller-provided and are not independently verified. Next: connect validated runtime events and addressed messages to relationship updates under explicit permissions, then add controlled cooperation experiments.
