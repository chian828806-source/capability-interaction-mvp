"""Fail closed when a sanitized task or ZERO condition exposes skills."""
from __future__ import annotations
from pathlib import Path
import subprocess
from common import FINAL_PREREGISTRATION, ROOT, read_json, write_json

def files(root: Path) -> list[str]: return [p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()]

def main() -> None:
    pre = read_json(FINAL_PREREGISTRATION); report = {"pass": True, "tasks": {}, "container_check": "docker bind-mount"}
    for task_id, spec in pre["tasks"].items():
        sanitized, zero = ROOT / "sanitized_tasks" / task_id, ROOT / "conditions" / task_id / "ZERO"
        leaked = [p for p in files(sanitized) if "/skills/" in f"/{p}"] if sanitized.exists() else ["sanitized task missing"]
        zero_files = files(zero) if zero.exists() else ["ZERO condition missing"]
        task_pass = not leaked and zero_files == ["manifest.json"]
        mounted = {}
        for label, selected in {"ZERO": [], "A": [spec["skills"][0]], "B": [spec["skills"][1]], "AB": spec["skills"]}.items():
            folder = ROOT / "conditions" / task_id / label
            cmd = ["docker", "run", "--rm", "-v", f"{folder}:/skills:ro", "ubuntu:24.04", "sh", "-lc", "find /skills -mindepth 1 -maxdepth 1 -type d -printf '%f\\n' | sort"]
            proc = subprocess.run(cmd, text=True, capture_output=True, check=False)
            exposed = [line for line in proc.stdout.splitlines() if line]
            mounted[label] = {"expected": selected, "exposed": exposed, "pass": proc.returncode == 0 and exposed == sorted(selected), "returncode": proc.returncode}
            task_pass &= mounted[label]["pass"]
        report["tasks"][task_id] = {"pass": task_pass, "sanitized_skill_paths": leaked, "zero_files": zero_files, "container_filesystem": mounted}
        report["pass"] &= task_pass
    write_json(ROOT / "reports" / "ISOLATION_REPORT.json", report)
    print("PASS" if report["pass"] else "FAIL", "— isolation report written")
    raise SystemExit(0 if report["pass"] else 1)

if __name__ == "__main__": main()
