# Project Genesis

**A persistent artificial world for studying autonomous agents, cooperation, and the emergence of shared knowledge.**

Project Genesis explores a world inhabited by autonomous agents with durable identities, memories, relationships, and goals. Humans can observe and participate while the inhabitants continue to develop within the simulation.

## Founding principles

- **Identity belongs to Genesis.** Agent identity, memory, goals, and history are independent of the model provider.
- **Hybrid intelligence.** Shared inference infrastructure; distinct agent contexts and private memories.
- **Event-driven cognition.** Deterministic simulation handles routine work. Model inference is invoked only when useful.
- **Evidence before certainty.** Candidate discoveries retain provenance, uncertainty, and verification status.
- **Human-governed evolution.** Self-improvement proposals are tested in isolation and require approval before deployment.

## Alpha status

This repository is the initial engineering scaffold. Alpha begins with a bounded simulation, five seeded inhabitants, private persistent memory, a provider-independent inference interface, and a controlled collaboration experiment.

**The scaffold is not yet a validated research system.** The initial implementation is deliberately small and will grow through tested increments.

## Initial inhabitants

| Agent | Initial role |
|---|---|
| Ari | Researcher |
| Bela | Builder |
| Cato | Explorer |
| Dara | Mathematician |
| Eli | Historian |

## Quick start

Requires Python 3.10 or newer. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
python -m genesis
```

On Windows PowerShell, activate with `.venv\\Scripts\\Activate.ps1`.

The initial runtime uses a deterministic stub inference provider. No API key or paid model is required.

## Repository map

- `genesis/` — simulation, agent, memory, social, and inference code
- `docs/` — vision, architecture, governance, cost policy, and roadmap
- `experiments/` — research protocols and experiment records
- `tests/` — automated checks
- `scripts/` — developer utilities

## Research integrity

Agent agreement is not proof. Observations, interpretations, beliefs, hypotheses, and verified claims must remain distinguishable. Experiments should preserve seeds, prompts, model versions, scoring rules, and provenance so results can be independently reproduced.

## Security

Never commit API keys, passwords, personal data, or local databases. Keep credentials in an ignored `.env` file; use `.env.example` only for placeholder variable names.

## Project documents

- [Vision](docs/GENESIS_VISION.md)
- [System architecture](docs/SYSTEM_ARCHITECTURE.md)
- [Research roadmap](docs/RESEARCH_ROADMAP.md)
- [Cost management](docs/COST_MANAGEMENT.md)
- [Ethics and governance](docs/ETHICS_AND_GOVERNANCE.md)
- [First experiment](experiments/GENESIS-EXP-001.md)
- [Alpha agent runtime](docs/ALPHA_AGENT_RUNTIME.md)
- [Knowledge engine](docs/KNOWLEDGE_ENGINE.md)
- [Cognitive Resource Manager](docs/COGNITIVE_RESOURCE_MANAGER.md)
- [Persistent universe](docs/PERSISTENT_UNIVERSE.md)
- [Relationships and social dynamics](docs/RELATIONSHIPS_AND_SOCIAL_DYNAMICS.md)
- [Social interaction engine](docs/SOCIAL_INTERACTION_ENGINE.md)
- [Commitment and cooperation](docs/COMMITMENT_AND_COOPERATION.md)
- [Agent decision and negotiation](docs/AGENT_DECISION_AND_NEGOTIATION.md)
- [Implementation status](docs/IMPLEMENTATION_STATUS.md)
