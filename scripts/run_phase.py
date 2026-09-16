"""Guarded phase runner. It never invents outcomes or silently changes models."""
from __future__ import annotations
import argparse, itertools, os, random, shlex, subprocess
from pathlib import Path
from common import ROOT, atomic_csv, now, read_json, sha256_file, write_json

CONDITIONS = ["ZERO", "A", "B", "AB"]

def prerequisite_errors(phase: str, model: str) -> list[str]:
    errors = []
    pricing = read_json(ROOT / "configs" / "pricing_snapshot.json")
    item = pricing.get("models", {}).get(model, {})
    if not pricing.get("date") or not pricing.get("source") or any(item.get(k) is None for k in ("input_price_per_1M", "output_price_per_1M")):
        errors.append("configs/pricing_snapshot.json lacks a dated, sourced price for the requested model")
    iso = ROOT / "reports" / "ISOLATION_REPORT.json"
    if not iso.exists() or not read_json(iso).get("pass"):
        errors.append("passing reports/ISOLATION_REPORT.json is required")
    for task in read_json(ROOT / "preregistration.yaml")["tasks"]:
        audit = ROOT / "task_audit" / f"{task}.json"
        if not audit.exists() or not read_json(audit).get("eligible"):
            errors.append(f"task {task} has no passing qualification audit")
    if not os.environ.get("API_KEY") or not os.environ.get("API_BASE_URL"):
        errors.append("API_KEY and API_BASE_URL must be environment variables")
    if not os.environ.get("MVP_RUNNER_TEMPLATE"):
        errors.append("MVP_RUNNER_TEMPLATE is required and must specify the fixed provider-agnostic harness")
    gates_path = ROOT / "reports" / "phase_gates.json"
    gates = read_json(gates_path) if gates_path.exists() else {}
    required_gate = {"screening": "pilot_passed", "confirmation": "negative_candidate", "cross_model": "confirmed_candidate"}.get(phase)
    if required_gate and gates.get(required_gate) is not True:
        errors.append(f"reports/phase_gates.json must set {required_gate}=true after reviewing the preceding phase")
    return errors

def planned_cost_upper_bound(model: str, pricing: dict, config: dict) -> float:
    # Conservative per-call cap; input context is unknown, so this is a guard not an estimate.
    prices = pricing["models"][model]
    output = float(prices["output_price_per_1M"]) * config["execution_guards"]["max_output_tokens_per_call"] / 1_000_000
    return output * config["execution_guards"]["max_api_calls_per_run"]

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("phase", choices=["pilot", "screening", "confirmation", "cross_model"]); parser.add_argument("--dry-run", action="store_true"); args = parser.parse_args()
    config, models, pre = read_json(ROOT / "configs" / "experiment.yaml"), read_json(ROOT / "configs" / "models.yaml"), read_json(ROOT / "preregistration.yaml")
    phase_spec = config["phases"][args.phase]; model = models[phase_spec["model_key"]]["id"]
    errors = prerequisite_errors(args.phase, model)
    if errors:
        raise SystemExit("Refusing to run:\n- " + "\n- ".join(errors))
    pricing = read_json(ROOT / "configs" / "pricing_snapshot.json")
    schedule = []
    for task_id in pre["tasks"]:
        for condition, rep in itertools.product(CONDITIONS, range(1, phase_spec["repetitions"] + 1)):
            schedule.append({"task_id": task_id, "condition": condition, "rep": rep})
    random.Random(config["random_seed"] + sum(map(ord, args.phase))).shuffle(schedule)
    projected = len(schedule) * planned_cost_upper_bound(model, pricing, config)
    prior = 0.0
    results = ROOT / "runs" / "results_long.csv"
    if results.exists():
        import csv
        with results.open(encoding="utf-8", newline="") as f: prior = sum(float(r.get("estimated_cost_usd") or 0) for r in csv.DictReader(f))
    if prior + projected > float(config["max_api_budget_usd"]):
        raise SystemExit(f"Budget guard: conservative projected total ${prior + projected:.2f} exceeds ${config['max_api_budget_usd']:.2f}.")
    atomic_csv(ROOT / "configs" / "run_schedule.csv", ["phase", "order", "task_id", "condition", "rep", "model"],
               [{"phase": args.phase, "order": i + 1, "model": model, **run} for i, run in enumerate(schedule)])
    frozen = {"phase": args.phase, "timestamp": now(), "config_sha256": sha256_file(ROOT / "configs" / "experiment.yaml"),
              "preregistration_sha256": sha256_file(ROOT / "preregistration.yaml"), "model": model, "schedule": schedule}
    write_json(ROOT / "configs" / f"frozen_{args.phase}.json", frozen)
    (ROOT / "PREREGISTRATION_HASH.txt").write_text(frozen["preregistration_sha256"] + "\n", encoding="utf-8")
    if args.dry_run:
        print(f"Dry run: frozen {len(schedule)} runs for {args.phase}; no API call made."); return
    template = os.environ["MVP_RUNNER_TEMPLATE"]
    for ordinal, run in enumerate(schedule, 1):
        run_id = f"{run['task_id']}__{model}__{run['condition']}__{run['rep']}"
        run_dir = ROOT / "runs" / "raw" / run_id; run_dir.mkdir(parents=True, exist_ok=False)
        values = {"task_dir": str(ROOT / "sanitized_tasks" / run["task_id"]), "skills_dir": str(ROOT / "conditions" / run["task_id"] / run["condition"]),
                  "condition": run["condition"], "model": model, "run_dir": str(run_dir), "seed": str(config["random_seed"] + ordinal)}
        cmd = template.format(**values)
        metadata = {"run_id": run_id, "timestamp_start": now(), "phase": args.phase, "task_id": run["task_id"], "skill_condition": run["condition"],
                    "model_provider": config["provider"], "requested_model": model, "reasoning_setting": config["reasoning_setting"], "infra_valid": None,
                    "runner_command": cmd, "run_schedule_order": ordinal}
        write_json(run_dir / "metadata.json", metadata)
        try:
            proc = subprocess.run(cmd, shell=True, cwd=ROOT, text=True, capture_output=True, timeout=config["execution_guards"]["max_wall_time_per_run_seconds"])
            (run_dir / "stdout.log").write_text(proc.stdout, encoding="utf-8"); (run_dir / "stderr.log").write_text(proc.stderr, encoding="utf-8")
            metadata.update({"timestamp_end": now(), "runner_returncode": proc.returncode, "infra_valid": proc.returncode == 0})
        except subprocess.TimeoutExpired as exc:
            (run_dir / "stdout.log").write_text(exc.stdout or "", encoding="utf-8"); (run_dir / "stderr.log").write_text((exc.stderr or "") + "\nTIMEOUT", encoding="utf-8")
            metadata.update({"timestamp_end": now(), "infra_valid": True, "failure_reason": "agent_timeout"})
        write_json(run_dir / "metadata.json", metadata)
        print(f"[{ordinal}/{len(schedule)}] {run_id}")

if __name__ == "__main__": main()
