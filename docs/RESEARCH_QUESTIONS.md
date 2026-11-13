# Research Questions

The questions Genesis exists to investigate, drawn from the master
specification (v0.2). Each question names what would count as evidence, so a
result — positive or negative — is meaningful.

## From the specification

1. **Distributed collaboration.** Can a group of agents solve a bounded
   problem that no individual can solve from its initial information —
   and is the benefit larger than simply pooling the information?
   *Evidence:* GENESIS-EXP-001, including its oracle control condition.
2. **Memory continuity.** Do inhabitants retain and correctly use knowledge
   across restarts and over time?
   *Evidence:* memory continuity and retrieval-accuracy metrics on held-out
   tasks; restart acceptance tests.
3. **Reproducible discovery.** Can a finding produced inside the world be
   independently reproduced from preserved seeds, prompts, and procedures?
   *Evidence:* the distillation pipeline yields at least one traceable
   candidate finding that an independent run reproduces.
4. **False discovery control.** How often do inhabitants produce confident
   claims that verification refutes, and does the knowledge engine's
   corroboration process reduce that rate?
   *Evidence:* false discovery rate tracked across experiment runs.

## Open questions adopted for later milestones

5. **Identity across models.** If the model behind an inhabitant is swapped
   mid-run, how much do its behaviour, memory use, and relationships drift?
   Small drift would evidence the founding principle that identity belongs
   to Genesis; large drift would show where identity actually lives.
6. **Calibration.** Does an inhabitant's stated confidence match its
   accuracy against ground truth the simulator knows? Can false beliefs be
   observed spreading between inhabitants, and does communication correct
   or amplify them?
7. **Considered refusal in practice.** When inhabitants may decline without
   penalty, do commitments become *more* reliable — because acceptances are
   genuine — or less? Measured by completion rates of accepted commitments
   before and after the decision and negotiation layer.

Behavioural sophistication is not evidence of consciousness. Consciousness
research remains a separate, cautious programme and no experiment here is
designed to claim it.
