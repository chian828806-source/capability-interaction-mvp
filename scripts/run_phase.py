"""Guarded phase runner. It never invents outcomes or silently changes models."""
from __future__ import annotations
import argparse, itertools, os, random, shlex, statistics, subprocess
from pathlib import Path
from common import FINAL_PREREGISTRATION, ROOT, atomic_csv, now, read_json, sha256_file, write_json

CONDITIONS = ["ZERO", "A", "B", "AB"]

def actual_cost(run_dir: Path, prices: dict) -> dict:
    """Price recorded input/cached-input/output tokens after every run."""
    usage = {}
    for name in ("usage.json", "result.json"):
        path = run_dir / name
        if path.exists():
            try: usage.update(read_json(path).get("usage", read_json(path)))
            except Exception: pass
    if not any(key in usage for key in ("input_tokens", "prompt_tokens", "output_tokens", "completion_tokens")):
        raise RuntimeError("usage missing; refusing to assign a zero cost")
    inp = int(usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0)
    cached = int(usage.get("cached_input_tokens", 0) or 0)
    out = int(usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0)
    total = (inp - cached) * float(prices["input_price_per_1M"]) / 1_000_000
    total += cached * float(prices.get("cached_input_price_per_1M") or prices["input_price_per_1M"]) / 1_000_000
    total += out * float(prices["output_price_per_1M"]) / 1_000_000
    return {"input_tokens": inp, "cached_input_tokens": cached, "output_tokens": out, "actual_cost_usd": total}

def prerequisite_errors(phase: str, model: str, dry_run: bool = False) -> list[str]:
    errors = []
    pricing = read_json(ROOT / "configs" / "pricing_snapshot.json")
    item = pricing.get("models", {}).get(model, {})
    if not dry_run and (not pricing.get("date") or not pricing.get("source") or any(item.get(k) is None for k in ("input_price_per_1M", "output_price_per_1M"))):
        errors.append("configs/pricing_snapshot.json lacks a dated, sourced price for the requested model")
    iso = ROOT / "reports" / "ISOLATION_REPORT.json"
    if not iso.exists() or not read_json(iso).get("pass"):
        errors.append("passing reports/ISOLATION_REPORT.json is required")
    for task in read_json(FINAL_PREREGISTRATION)["tasks"]:
        audit = ROOT / "task_audit" / f"{task}.json"
        if not audit.exists() or not read_json(audit).get("eligible"):
            errors.append(f"task {task} has no passing qualification audit")
    if not dry_run and (not os.environ.get("API_KEY") or not os.environ.get("API_BASE_URL")):
        errors.append("API_KEY and API_BASE_URL must be environment variables")
    if not dry_run and not os.environ.get("MVP_RUNNER_TEMPLATE"):
        errors.append("MVP_RUNNER_TEMPLATE is required and must specify the fixed provider-agnostic harness")
    gates_path = ROOT / "reports" / "phase_gates.json"
    gates = read_json(gates_path) if gates_path.exists() else {}
    required_gate = {"screening": "pilot_passed", "confirmation": "negative_candidate", "cross_model": "confirmed_candidate"}.get(phase)
    if required_gate and gates.get(required_gate) is not True:
        errors.append(f"reports/phase_gates.json must set {required_gate}=true after reviewing the preceding phase")
    return errors

def planned_cost_upper_bound(model: str, pricing: dict, config: dict) -> float:
    # Both input and output caps are budgeted conservatively.
    prices = pricing["models"][model]
    input_ = float(prices["input_price_per_1M"]) * config["execution_guards"].get("max_input_tokens_per_call", 16384) / 1_000_000
    output = float(prices["output_price_per_1M"]) * config["execution_guards"]["max_output_tokens_per_call"] / 1_000_000
    return (input_ + output) * config["execution_guards"]["max_api_calls_per_run"]

def budget_snapshot(costs: list[float], remaining_runs: int, upper_per_run: float) -> dict:
    median = statistics.median(costs) if costs else 0.0
    p90 = sorted(costs)[max(0, int(len(costs) * 0.9 + 0.999999) - 1)] if costs else 0.0
    observed_per_run = max(median, p90)
    projected_per_run = max(observed_per_run, upper_per_run)
    return {"actual_cost_usd": sum(costs), "median_run_cost_usd": median, "p90_run_cost_usd": p90,
            "projected_remaining_cost_usd": remaining_runs * projected_per_run,
            "projected_total_cost_usd": sum(costs) + remaining_runs * projected_per_run}

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("phase", choices=["pilot", "screening", "confirmation", "cross_model"]); parser.add_argument("--dry-run", action="store_true"); args = parser.parse_args()
    config, models, pre = read_json(ROOT / "configs" / "experiment.yaml"), read_json(ROOT / "configs" / "models.yaml"), read_json(FINAL_PREREGISTRATION)
    phase_spec = config["phases"][args.phase]; model = models[phase_spec["model_key"]]["id"]
    errors = prerequisite_errors(args.phase, model, args.dry_run)
    if errors:
        raise SystemExit("Refusing to run:\n- " + "\n- ".join(errors))
    pricing = read_json(ROOT / "configs" / "pricing_snapshot.json")
    schedule = []
    selected = list(pre["tasks"])
    if args.phase in {"confirmation", "cross_model"}:
        candidates = read_json(ROOT / "reports" / "candidate_gates.json").get("selected_candidates", []) if (ROOT / "reports" / "candidate_gates.json").exists() else []
        selected = [c["task_id"] for c in candidates]
        if not selected: raise SystemExit("No preregistered candidate selection exists for this phase.")
    for task_id in selected:
        for condition, rep in itertools.product(CONDITIONS, range(1, phase_spec["repetitions"] + 1)):
            schedule.append({"task_id": task_id, "condition": condition, "rep": rep})
    random.Random(config["random_seed"] + sum(map(ord, args.phase))).shuffle(schedule)
    projected = len(schedule) * planned_cost_upper_bound(model, pricing, config) if not args.dry_run else 0.0
    prior = 0.0; historical_costs = []
    results = ROOT / "runs" / "results_long.csv"
    if results.exists():
        import csv
        with results.open(encoding="utf-8", newline="") as f:
            historical_costs = [float(r.get("actual_cost_usd") or r.get("estimated_cost_usd") or 0) for r in csv.DictReader(f)]
            prior = sum(historical_costs)
    if prior + projected > float(config["max_api_budget_usd"]):
        raise SystemExit(f"Budget guard: conservative projected total ${prior + projected:.2f} exceeds ${config['max_api_budget_usd']:.2f}.")
    atomic_csv(ROOT / "configs" / "run_schedule.csv", ["phase", "order", "task_id", "condition", "rep", "model"],
               [{"phase": args.phase, "order": i + 1, "model": model, **run} for i, run in enumerate(schedule)])
    frozen = {"phase": args.phase, "timestamp": now(), "config_sha256": sha256_file(ROOT / "configs" / "experiment.yaml"),
              "preregistration_sha256": sha256_file(FINAL_PREREGISTRATION), "model": model, "schedule": schedule}
    write_json(ROOT / "configs" / f"frozen_{args.phase}.json", frozen)
    if args.dry_run:
        write_json(ROOT / "configs" / "budget_snapshot.json", budget_snapshot(historical_costs, len(schedule), 0.0))
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
            text = (proc.stdout + "\n" + proc.stderr).lower()
            agent_failure = any(x in text for x in ("agent_timeout", "max_steps", "max_api_calls"))
            metadata.update({"timestamp_end": now(), "runner_returncode": proc.returncode, "infra_valid": proc.returncode == 0 or agent_failure,
                             "failure_class": "AGENT_FAILURE" if agent_failure else ("INFRASTRUCTURE_FAILURE" if proc.returncode else None)})
            metadata.update(actual_cost(run_dir, pricing["models"][model]))
            prior += metadata["actual_cost_usd"]
            historical_costs.append(metadata["actual_cost_usd"])
            snapshot = budget_snapshot(historical_costs, len(schedule) - ordinal, planned_cost_upper_bound(model, pricing, config))
            write_json(ROOT / "configs" / "budget_snapshot.json", snapshot)
            if snapshot["projected_total_cost_usd"] > float(config["max_api_budget_usd"]):
                metadata["budget_hard_stop"] = True
                write_json(run_dir / "metadata.json", metadata)
                raise SystemExit("Budget hard stop: actual/median/p90 projected total exceeds the $15 cap.")
        except subprocess.TimeoutExpired as exc:
            (run_dir / "stdout.log").write_text(exc.stdout or "", encoding="utf-8"); (run_dir / "stderr.log").write_text((exc.stderr or "") + "\nTIMEOUT", encoding="utf-8")
            metadata.update({"timestamp_end": now(), "infra_valid": True, "failure_reason": "agent_timeout", "failure_class": "AGENT_FAILURE"})
            metadata.update(actual_cost(run_dir, pricing["models"][model]))
        write_json(run_dir / "metadata.json", metadata)
        print(f"[{ordinal}/{len(schedule)}] {run_id}")

if __name__ == "__main__": main()
