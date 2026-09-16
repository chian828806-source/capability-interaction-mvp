# Capability Interaction MVP

Reproducible implementation of the fixed SkillsBench v1.1 screening protocol.

## Frozen preflight status

This is a pre-Pilot frozen snapshot. **No paid model or API run has been
made.** The local WSL/Docker/BenchFlow 0.6.7 execution chain, oracle, and
verifier have been qualified for two replacement tasks.

- Task 1: `adaptive-cruise-control` — three fresh oracle rewards of `1.0`;
  verifier 12/12 on each run.
- Task 2: `hvac-control` — three fresh oracle rewards of `1.0`; verifier 7/7
  on each run.
- Frozen task-pair configuration: `preregistration_v2.yaml`, SHA-256 in
  `PREREGISTRATION_HASH_V2.txt`.

The retired BugSwarm tasks are recorded as semantic external-dependency
failures. Runtime package installation is classified separately as a bootstrap
dependency; it is not treated as task ground truth.

## Fixed design

- Benchmark: SkillsBench `v1.1`, commit `b63b7b2`.
- Task 1: `adaptive-cruise-control`; A=`vehicle-dynamics`,
  B=`pid-controller`.
- Task 2: `hvac-control`; A=`first-order-model-fitting`,
  B=`imc-tuning-rules`.
- Pilot: `gpt-5.4-nano-2026-03-17`; formal phases:
  `gpt-5.4-mini-2026-03-17`; cross-model only after confirmation:
  `gemini-3.8-flash`.
- Budget ceiling: USD 15.00.  No automatic model routing is permitted.

## Reproduce the preflight

1. Obtain the exact public benchmark source from WSL with a repository-local
   LF checkout (do not change global Git settings):
   `git -c core.autocrlf=false clone --branch v1.1 https://github.com/benchflow-ai/skillsbench.git external/skillsbench-lf`
2. Verify `git -C external/skillsbench-lf rev-parse --short HEAD` reports
   `b63b7b2`; install the compatible BenchFlow line and start Docker.
3. Recreate the static inventory with
   `python scripts/scan_task_candidates.py`; inspect
   `task_audit/task_candidate_inventory.csv` and the reports before any new
   qualification work.
4. Fill the same-day provider prices in `configs/pricing_snapshot.json` and
   export credentials only as environment variables.  Never add credentials to
   this repository.
5. Run `python scripts/run_pilot.py`.  The phase runners refuse to run until
   the preflight prerequisites and the declared budget are satisfied.

Qualification evidence and selection rationale are in
`reports/TASK_REPLACEMENT_AUDIT.md` and `reports/TASK_CANDIDATE_SWEEP.md`.
Do not start a paid Pilot until the skill-pair freeze is explicitly reviewed.

The model runner command is deliberately supplied through the environment
variable `MVP_RUNNER_TEMPLATE`, rather than hard-coded.  It must use the same
provider-agnostic harness for all conditions within a model comparison.  Its
available substitutions are documented in `configs/experiment.yaml`.

## Analysis

After each phase, use `python scripts/collect_results.py`, followed by
`python analysis/summarize.py`, `python analysis/interaction.py`,
`python analysis/bayesian_interaction.py`, `python analysis/utilization_analysis.py`,
`python analysis/cost_analysis.py`, and `python analysis/make_figures.py`.
All derived outputs are written under `reports/` and `figures/`; raw run data
remains in `runs/raw/`.
