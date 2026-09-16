from __future__ import annotations
import csv, json, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONDITIONS = ("ZERO", "A", "B", "AB")

def rows():
    path = ROOT / "runs" / "results_long.csv"
    if not path.exists(): return []
    with path.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))

def valid(data):
    return [r for r in data if str(r.get("valid", "")).lower() == "true" and r.get("verifier_result") in {"PASS", "FAIL"}]

def groups(data):
    out = {}
    for row in valid(data): out.setdefault((row["task_id"], row["requested_model"], row["skill_condition"]), []).append(row)
    return out

def rate(records):
    n = len(records); k = sum(r["verifier_result"] == "PASS" for r in records)
    return (k / n if n else None), k, n

def wilson(k, n, z=1.96):
    if not n: return None, None
    d = 1 + z*z/n; c = (k/n + z*z/(2*n))/d; h = z/d * math.sqrt((k/n*(1-k/n)+z*z/(4*n))/n)
    return c-h, c+h

def dump(name, value):
    path = ROOT / "reports" / name; path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
