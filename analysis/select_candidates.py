"""Deterministically select Screening candidates using every frozen gate."""
from __future__ import annotations

import csv
import json
from pathlib import Path

from bayesian_interaction import main as write_bayesian_interaction

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    pre = json.loads((ROOT / "preregistration_final.yaml").read_text(encoding="utf-8"))
    results = ROOT / "runs" / "results_long.csv"
    rows = list(csv.DictReader(results.open(encoding="utf-8"))) if results.exists() else []
    # This calls the frozen seeded posterior calculation and consumes P_I_lt_0.
    write_bayesian_interaction()
    posterior_rows = json.loads((ROOT / "reports" / "bayesian_interaction.json").read_text(encoding="utf-8"))
    posterior = {(item["task_id"], item["model"]): item for item in posterior_rows}
    gate = pre["gates"]
    candidates = []
    for task_id in pre["tasks"]:
        task_rows = [row for row in rows if row.get("phase") == "screening" and row.get("task_id") == task_id and row.get("valid") == "True"]
        for model in sorted({row.get("requested_model") for row in task_rows}):
            model_rows = [row for row in task_rows if row.get("requested_model") == model]
            rates = {condition: sum(row["verifier_result"] == "PASS" for row in model_rows if row["skill_condition"] == condition) / max(1, sum(row["skill_condition"] == condition for row in model_rows)) for condition in pre["conditions"]}
            contrast = rates["AB"] - rates["A"] - rates["B"] + rates["ZERO"]
            posterior_item = posterior.get((task_id, model))
            p_negative = posterior_item.get("P_I_lt_0") if posterior_item else None
            passes = (rates["A"] - rates["ZERO"] >= gate["candidate_main_effect"]
                      and rates["B"] - rates["ZERO"] >= gate["candidate_main_effect"]
                      and min(rates["A"], rates["B"]) - rates["AB"] >= gate["candidate_ab_drop"]
                      and p_negative is not None and p_negative >= gate["candidate_p_negative"])
            if passes:
                candidates.append({"task_id": task_id, "model": model, "contrast": contrast, "ab_rate": rates["AB"], "P_I_lt_0": p_negative, "rates": rates})
    candidates.sort(key=lambda value: (value["contrast"], value["ab_rate"], value["task_id"]))
    output = {"selected_candidates": candidates[:1], "all_candidates": candidates, "gates": {key: gate[key] for key in ("candidate_main_effect", "candidate_ab_drop", "candidate_p_negative")}, "rule": pre["candidate_resolution"]}
    (ROOT / "reports" / "candidate_gates.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
