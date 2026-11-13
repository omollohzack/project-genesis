# Social Interaction Engine

## Purpose

This milestone connects addressed messages to relationship history without treating communication itself as proof of trustworthiness. Messages remain neutral until a participant records an outcome.

## Flow

1. An agent sends a direct message through `CommunicationStore`.
2. Only the sender or recipient can retrieve that message through `get_message`.
3. A participant records one typed outcome through `SocialInteractionEngine.record_outcome`.
4. The engine maps the outcome to a fixed, bounded trust adjustment.
5. It atomically records the outcome, relationship event, and derived relationship update in the same SQLite database.

## Outcome catalog

| Outcome | Trust adjustment | Cooperation count |
|---|---:|---:|
| neutral | 0.00 | no |
| helpful | +0.10 | yes |
| cooperation | +0.10 | yes |
| commitment_fulfilled | +0.15 | yes |
| disagreement | -0.03 | no |
| conflict | -0.10 | no |
| commitment_broken | -0.20 | no |

Cumulative trust remains bounded to [-1, +1]. The catalog is deliberately small and transparent; no model-generated numeric score is accepted.

## Perspective and duplicate handling

The sender and recipient may each record their own perspective. Their relationship records remain directional. Each participant can record at most one outcome per message; repeating the same submission returns the original event ID and does not apply the score twice.

A non-participant cannot retrieve or rate a message. The observer must be an active inhabitant in the supplied world.

## Important limitations

- Outcomes are explicitly supplied by the caller. This version does not decide whether a promise was actually fulfilled or whether a message led to real cooperation.
- The engine records a participant's perspective, not an objective verdict. Conflicting accounts are allowed.
- It does not yet provide a fully authenticated agent API, commitment/task objects, negotiation protocols, or automatic social reasoning.
- Message and relationship stores must use the same SQLite database file for the atomic transaction.
- SQLite is still a single-host prototype; production concurrency, migrations, backup and retention need further work.

The next research step is to connect explicit commitments and completed world actions to independently observable outcome evidence, then test whether relationship history improves cooperation in controlled experiments.
