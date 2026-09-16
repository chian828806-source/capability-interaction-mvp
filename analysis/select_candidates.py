"""Deterministically select a Screening candidate using frozen gates."""
import csv, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
pre = json.loads((ROOT / "preregistration_final.yaml").read_text())
rows = list(csv.DictReader((ROOT / "runs" / "results_long.csv").open())) if (ROOT / "runs" / "results_long.csv").exists() else []
candidates = []
for task_id in pre["tasks"]:
    task_rows = [r for r in rows if r.get("phase") == "screening" and r.get("task_id") == task_id and r.get("valid") == "True"]
    if not task_rows:
        continue
    rates = {condition: sum(r["verifier_result"] == "PASS" for r in task_rows if r["skill_condition"] == condition) / max(1, sum(r["skill_condition"] == condition for r in task_rows)) for condition in pre["conditions"]}
    contrast = rates["AB"] - rates["A"] - rates["B"] + rates["ZERO"]
    gate = pre["gates"]
    if rates["A"] - rates["ZERO"] >= gate["candidate_main_effect"] and rates["B"] - rates["ZERO"] >= gate["candidate_main_effect"] and min(rates["A"], rates["B"]) - rates["AB"] >= gate["candidate_ab_drop"] and contrast < 0:
        candidates.append({"task_id": task_id, "contrast": contrast, "ab_rate": rates["AB"]})
candidates.sort(key=lambda value: (value["contrast"], value["ab_rate"], value["task_id"]))
(ROOT / "reports" / "candidate_gates.json").write_text(json.dumps({"selected_candidates": candidates[:1], "all_candidates": candidates, "rule": pre["candidate_resolution"]}, indent=2) + "\n")
