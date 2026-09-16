"""Derive a long-format table from immutable per-run records without omission."""
from __future__ import annotations
import csv, json
from pathlib import Path
from common import ROOT, atomic_csv, now, read_json

FIELDS = ["run_id", "timestamp_start", "timestamp_end", "phase", "task_id", "skill_condition", "model_provider", "requested_model", "returned_model", "reasoning_setting", "verifier_result", "verifier_score", "valid", "infra_valid", "failure_reason", "failure_class", "input_tokens", "cached_input_tokens", "output_tokens", "reasoning_tokens", "number_of_api_calls", "retry_count", "actual_cost_usd", "estimated_cost_usd", "wall_clock_time", "tool_calls", "skill_A_available", "skill_B_available", "skill_A_loaded", "skill_B_loaded", "skill_load_order", "files_changed"]

def verifier_result(run_dir: Path, metadata: dict) -> str:
    result = run_dir / "result.json"
    if result.exists():
        try:
            value = json.loads(result.read_text(encoding="utf-8")); raw = str(value.get("verifier_result", value.get("status", ""))).upper()
            if raw in {"PASS", "FAIL"}: return raw
        except json.JSONDecodeError: pass
    log = (run_dir / "verifier.log")
    text = log.read_text(encoding="utf-8", errors="replace").upper() if log.exists() else ""
    if "PASS" in text and "FAIL" not in text: return "PASS"
    if "FAIL" in text: return "FAIL"
    return "UNRESOLVED"

def main() -> None:
    rows = []
    for run_dir in sorted(p for p in (ROOT / "runs" / "raw").iterdir() if p.is_dir()):
        meta_path = run_dir / "metadata.json"
        if not meta_path.exists(): continue
        meta = json.loads(meta_path.read_text(encoding="utf-8")); result=read_json(run_dir/"result.json") if (run_dir/"result.json").exists() else {}; usage=read_json(run_dir/"usage.json") if (run_dir/"usage.json").exists() else {}; calls=read_json(run_dir/"tool_calls.json") if (run_dir/"tool_calls.json").exists() else []
        meta={**meta,**result,**usage,"tool_calls":len(calls)}; verdict = verifier_result(run_dir, meta)
        infra = meta.get("infra_valid")
        if meta.get("failure_class") == "AGENT_FAILURE": verdict = "FAIL"
        if infra and meta.get("actual_cost_usd") is None:
            raise SystemExit(f"Fail closed: valid run {run_dir.name} lacks actual_cost_usd")
        row = {key: meta.get(key) for key in FIELDS}; row.update({"verifier_result": verdict, "infra_valid": infra,
            "valid": bool(infra) and verdict in {"PASS", "FAIL"}, "skill_A_available": meta.get("skill_condition") in {"A", "AB"}, "skill_B_available": meta.get("skill_condition") in {"B", "AB"}})
        rows.append(row)
    atomic_csv(ROOT / "runs" / "results_long.csv", FIELDS, rows)
    print(f"Collected {len(rows)} run records at {now()}.")

if __name__ == "__main__": main()
