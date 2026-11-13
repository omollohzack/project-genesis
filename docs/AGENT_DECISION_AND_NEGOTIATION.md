# Agent Decision and Negotiation Layer

## Purpose

This Alpha subsystem provides explainable decision support before an inhabitant accepts a proposed commitment. It checks configured capabilities, declared resources, concurrent accepted commitments, deadlines, and a lightweight match against the agent's stated goals.

The engine produces a recommendation; it does **not** accept or decline on the inhabitant's behalf.

## Operational profiles

A controller can register a world-scoped profile for an agent:
- capabilities: explicit skill labels
- resources: available quantities, e.g. `{"energy": 5, "tools": 2}`
- maximum active commitments

Profiles are stored separately from identity and private episodic memory. Updating a profile replaces its declared available-resource snapshot; this prototype does not reserve or decrement resources when work is accepted. A production resource ledger must add reservations and reconcile consumption.

## Evaluation

`AgentDecisionEngine.evaluate(world, commitment_id, agent_id)` returns:
- recommendation: `accept`, `decline`, or `negotiate`
- a heuristic score between 0 and 1 (not a probability)
- human-readable reasons
- a persisted decision ID and tick

Missing capability or resource requirements and exhausted capacity are hard negative signals. A missing profile is treated as uncertainty and recommends negotiation, not automatic rejection. Near deadlines lower the score. Goal matching is a deliberately simple keyword heuristic and must not be treated as deep understanding.

The requirement metadata `required_capabilities` and `required_resources` may be included in a commitment's expected payload. These fields inform feasibility evaluation and are excluded from completion-event matching; all other expected payload fields remain evidence requirements.

## Negotiation

The assigned inhabitant can submit a counterproposal with an extended deadline and rationale. The original proposer can accept or reject it. Acceptance updates the original still-open commitment's deadline and appends a `terms_revised` history entry in the same SQLite database. Rejection leaves the original terms unchanged.

Only deadline extensions are supported in this version. Scope changes, resource renegotiation, multi-party negotiation, and concurrent counterproposal conflict resolution remain future work.

## Example

```python
from genesis.social.decision import AgentDecisionEngine

engine = AgentDecisionEngine("genesis.db")
engine.set_profile(
    world, "cato",
    capabilities=["survey", "navigation"],
    resources={"energy": 5, "mapping_tools": 1},
    max_active_commitments=2,
)
recommendation = engine.evaluate(world, commitment_id, "cato")
# The agent/runtime must make an explicit response separately.
```

## Safety and limitations

- This is deterministic decision support, not autonomous cognition.
- A score is a heuristic, not a calibrated probability.
- Goals are matched with simple keywords.
- Profiles and agent IDs are currently supplied by the controller/caller; autonomous agent access needs authenticated principals and permission checks.
- Resources are checked but not reserved, so concurrent commitments can overbook them.
- The counterproposal protocol currently revises only deadlines.
- All records use SQLite and inherit its single-host prototype limitations.
