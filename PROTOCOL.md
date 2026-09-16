# Frozen protocol record

This repository implements the provided *LLM Agent Capability Interaction
Minimum Validation Protocol (MVP)* and its API/budget addendum.  The source
documents remain at the parent workspace root and should be retained as the
authoritative full text.  This concise record freezes the operational choices
used by the scripts.

The primary outcome is deterministic verifier pass/fail.  The four conditions
are `ZERO`, `A`, `B`, and `AB`; each receives a fresh sandbox.  The primary
contrast is `I_AB = p_AB - p_A - p_B + p_0`.  A negative-interaction candidate
requires both single skills to improve pass rate by at least 0.20, `AB` to be
at least 0.20 worse than the weaker single-skill condition, and a negative
contrast.  Candidate confirmation, matched irrelevant-skill controls, and
cross-model replication are gated exactly as described in the source protocol.

No LLM judge is a primary outcome.  Infrastructure failures are invalid rather
than task failures; valid task failures remain in the dataset.  Original skill
content must not be edited, verifier content must not be changed, and all
formal configurations are hashed before model execution.

## Documented compatibility deviation

The supplied protocol specifies BenchFlow `>=0.6.4,<0.7`.  The official
SkillsBench v1.1 release currently documents `>=0.6.3,<0.7`.  The stricter
protocol range is retained in `configs/experiment.yaml`; if an available
install cannot meet it, record the exact version and a rationale in
`PROTOCOL_DEVIATIONS.md` before any paid run.
