# Reproduction guide

Run all commands from the repository root with a Python 3.12+ environment.
This frozen snapshot stops before any paid Pilot.

```text
git -c core.autocrlf=false clone --branch v1.1 https://github.com/benchflow-ai/skillsbench.git external/skillsbench-lf
python scripts/scan_task_candidates.py
```

Confirm the inventory has 87 rows and verify the frozen task selection in
`preregistration_v2.yaml` against `PREREGISTRATION_HASH_V2.txt`. See
`reports/TASK_REPLACEMENT_AUDIT.md` for the three fresh oracle results per
qualified task.

Do not proceed to a paid Pilot without explicit review. Populate the provider's
same-day prices in `configs/pricing_snapshot.json` and supply `API_BASE_URL`
and `API_KEY` only as environment variables. Define `MVP_RUNNER_TEMPLATE` for
the reviewed provider-agnostic BenchFlow/OpenCode harness, then execute the
appropriate phase script. Each phase is scheduled deterministically and frozen
before execution. Finally:

```text
python scripts/collect_results.py
python analysis/summarize.py
python analysis/interaction.py
python analysis/bayesian_interaction.py
python analysis/utilization_analysis.py
python analysis/cost_analysis.py
python analysis/make_figures.py
```

Keep `runs/raw/` intact. Do not edit `runs/results_long.csv` manually.
