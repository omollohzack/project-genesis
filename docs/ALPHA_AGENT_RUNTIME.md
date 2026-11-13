# Alpha Agent Runtime

## Scope
This milestone adds a replaceable agent-policy boundary, bounded observations, validated actions, private episodic reflection, and explicit direct messages.

## Decision cycle
1. Runtime builds an observation from the public world event log and the agent's own goals.
2. A policy proposes one action.
3. Runtime validates the action type and payload.
4. Permitted effects are persisted as owner-scoped memory and world events.

The included ReflectivePolicy is deterministic scaffolding. It is not an LLM, does not establish autonomous intelligence, and must not be presented as consciousness.

## Privacy and communication
Private memory is never automatically inserted into another agent's observation. Direct messages are addressed to one recipient. Inbox retrieval is recipient-scoped; sent-message retrieval is sender-scoped. This Alpha interface has no broadcast or unrestricted world-chat operation.

## Known limitations
- The per-agent event cursor is currently in-memory and resets when the runtime restarts.
- The policy is synchronous and deterministic; no paid provider is configured.
- Message sharing is explicit but does not yet create verified shared knowledge.
- Relationship modelling, durable snapshots, migrations, and a full scheduler remain future work.
