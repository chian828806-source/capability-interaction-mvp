"""Fail closed when a sanitized task or ZERO condition exposes skills."""
from __future__ import annotations
from pathlib import Path
from common import ROOT, read_json, write_json

def files(root: Path) -> list[str]: return [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]

def main() -> None:
    pre = read_json(ROOT / "preregistration.yaml"); report = {"pass": True, "tasks": {}}
    for task_id, spec in pre["tasks"].items():
        sanitized, zero = ROOT / "sanitized_tasks" / task_id, ROOT / "conditions" / task_id / "ZERO"
        leaked = [p for p in files(sanitized) if "/skills/" in f"/{p}"] if sanitized.exists() else ["sanitized task missing"]
        zero_files = files(zero) if zero.exists() else ["ZERO condition missing"]
        task_pass = not leaked and zero_files == ["manifest.json"]
        report["tasks"][task_id] = {"pass": task_pass, "sanitized_skill_paths": leaked, "zero_files": zero_files}
        report["pass"] &= task_pass
    write_json(ROOT / "reports" / "ISOLATION_REPORT.json", report)
    print("PASS" if report["pass"] else "FAIL", "— isolation report written")
    raise SystemExit(0 if report["pass"] else 1)

if __name__ == "__main__": main()
