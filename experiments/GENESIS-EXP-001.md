# GENESIS-EXP-001 — Emergent Knowledge Through Distributed Collaboration

## Research question
Does communication combined with persistent memory improve a group's ability to solve a bounded problem when relevant clues are distributed across agents?

## Conditions
1. **Independent:** agents solve without communication.
2. **Communication only:** agents exchange messages, but no persistent memory is available between sessions.
3. **Communication + memory:** agents exchange messages and retrieve their own persistent memories.
4. **Oracle control:** a single agent receives the union of all clue subsets, with communication and memory available. This separates genuine collaboration benefit from mere information pooling: if the oracle matches the group's performance, distributing the clues added nothing.

## Design
Give five agents different subsets of clues about a bounded, objectively scoreable task. Use multiple task instances and randomized or counterbalanced clue assignments. Define scoring before trials. Keep model/provider versions, prompts, seeds, and task conditions fixed or explicitly recorded. Use invented names, rules, and resources for task content wherever possible, so success cannot come from a model's memorized knowledge of the task domain, and prefer tasks whose ground truth can be checked mechanically (for example with SymPy).

## Measures
Accuracy and completeness; information exchange; steps and elapsed simulation time; contribution by agent; unsupported claims and uncertainty; reproducibility; inference calls, tokens, latency, and cost.

## Integrity requirements
One successful run is not sufficient. Preserve raw event logs and task ground truth. Compare against a deterministic baseline where possible. Distinguish observed facts from interpretations and hypotheses. Do not infer general intelligence or consciousness from task performance.

## Status
Protocol drafted; implementation and preregistered scoring remain to be completed.
