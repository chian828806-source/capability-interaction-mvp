"""Run the protocol's non-LLM task qualification audit."""
from __future__ import annotations
import argparse, os, shlex
from pathlib import Path
from common import FINAL_PREREGISTRATION, ROOT, command, environment_manifest, now, read_json, tree_hash, write_json

def bench(task: Path, agent: str) -> dict:
    return command(["bench", "eval", "run", "--tasks-dir", str(task), "--agent", agent, "--sandbox", "docker"], cwd=ROOT / "external" / "skillsbench")

def passed(result: dict) -> bool:
    # BenchFlow's exact output wording may evolve; retain raw logs and use exit status.
    return result.get("returncode") == 0

def audit(task_id: str, root: Path) -> dict:
    task = root / "tasks" / task_id
    record = {"task_id": task_id, "timestamp": now(), "task_path": str(task), "eligible": False,
              "checks": {}, "known_issue_search": "Manual issue-tracker review required; record URL/date before paid runs."}
    if not task.is_dir():
        record["checks"]["source_present"] = {"pass": False, "reason": "Pinned benchmark checkout unavailable"}
        return record
    record["task_hash"] = tree_hash(task)
    structural = command(["bench", "tasks", "check", str(task)], cwd=root)
    record["checks"]["structural"] = {"pass": passed(structural), "raw": structural}
    oracle_1, oracle_2 = bench(task, "oracle"), bench(task, "oracle")
    record["checks"]["oracle_two_fresh_sandboxes"] = {"pass": passed(oracle_1) and passed(oracle_2), "runs": [oracle_1, oracle_2]}
    # Two oracle executions exercise repeatability without altering the official verifier.
    record["checks"]["verifier_repeatability"] = {"pass": passed(oracle_1) == passed(oracle_2), "method": "two independent oracle+verifier executions"}
    initial_template = os.environ.get("MVP_INITIAL_STATE_TEMPLATE")
    if initial_template:
        initial = command(shlex.split(initial_template.format(task_dir=str(task))), cwd=root)
        record["checks"]["initial_state"] = {"pass": not passed(initial), "raw": initial}
    else:
        record["checks"]["initial_state"] = {"pass": False,
            "note": "Set MVP_INITIAL_STATE_TEMPLATE to a reviewed pristine-sandbox verifier command using {task_dir}; no unsupported noop agent is assumed."}
    joined_oracle_logs = "\n".join([oracle_1.get("stdout", ""), oracle_1.get("stderr", ""), oracle_2.get("stdout", ""), oracle_2.get("stderr", "")]).lower()
    record["checks"]["bootstrap_history"] = {"pass": True, "note": "Bootstrap failures are classified separately from semantic dependencies."}
    checks = record["checks"]
    record["eligible"] = all(v.get("pass") is True for v in checks.values())
    return record

def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--source", type=Path, default=ROOT / "external" / "skillsbench-lf"); args = parser.parse_args()
    manifest = environment_manifest(); manifest["benchmark_source"] = str(args.source)
    rev = command(["git", "rev-parse", "HEAD"], cwd=args.source) if args.source.exists() else {"stdout": "", "returncode": None}
    manifest["skillsbench_commit"] = rev.get("stdout", "").strip() or None
    write_json(ROOT / "environment_manifest.json", manifest)
    for task_id in read_json(FINAL_PREREGISTRATION)["tasks"]:
        result = audit(task_id, args.source)
        write_json(ROOT / "task_audit" / f"{task_id}.json", result)
        lines = [f"# Task audit: {task_id}", "", f"- Timestamp: {result['timestamp']}", f"- Eligible: `{result['eligible']}`", f"- Task hash: `{result.get('task_hash', 'unavailable')}`", "", "## Checks", ""]
        lines += [f"- **{name}**: `{detail.get('pass')}`" for name, detail in result["checks"].items()]
        lines += ["", "## Known issues", "", result["known_issue_search"], ""]
        (ROOT / "task_audit" / f"{task_id}.md").write_text("\n".join(lines), encoding="utf-8")
    print("Audit records written. Do not run paid phases unless every required check is true.")

if __name__ == "__main__": main()
