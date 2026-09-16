# MVP Preflight Report — frozen replacement selection

## Status

- Benchmark: SkillsBench v1.1 commit `b63b7b2850226b6aa4fb5929a8c1ac7bc4d9a6af`
- Runner: BenchFlow `0.6.7`, WSL + Docker, project-local LF checkout
- Qualified Task 1: `adaptive-cruise-control` — 3× oracle `1.0`, verifier
  12/12 per run, `no-skill` oracle configuration
- Qualified Task 2: `hvac-control` — 3× oracle `1.0`, verifier 7/7 per run,
  `no-skill` oracle configuration
- Paid model/API runs: not started
- Frozen status: `READY_FOR_SKILL_PAIR_FREEZE`

The complete static sweep of 87 tasks is in
`task_audit/task_candidate_inventory.csv`. The task selection and recommended
skill pairs are documented in `TASK_CANDIDATE_SWEEP.md`; runtime bootstrap and
semantic external dependencies are distinguished in `TASK_REPLACEMENT_AUDIT.md`.

The original BugSwarm tasks remain retired because their oracles obtain golden
patches from the BugSwarm REST API, a semantic external dependency. The
original preregistration is preserved; the frozen replacement selection is in
`preregistration_v2.yaml` with its SHA-256 sidecar.
