"""Run one real BenchFlow/OpenCode ACP rollout and normalize its artifacts."""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from common import now, read_json, write_json


def rollout(root: Path) -> Path | None:
    found = sorted(root.rglob("result.json"), key=lambda path: path.stat().st_mtime)
    return found[-1].parent if found else None


def first_value(*values: Any) -> Any:
    return next((value for value in values if value is not None), None)


def normalize_usage(result: dict[str, Any]) -> dict[str, Any]:
    """Map BenchFlow 0.6.7's result schema to the experiment's stable schema."""
    agent = result.get("agent_result") or {}
    metrics = result.get("final_metrics") or {}
    return {
        "input_tokens": first_value(agent.get("n_input_tokens"), metrics.get("total_prompt_tokens")),
        "cached_input_tokens": first_value(agent.get("n_cache_read_tokens"), metrics.get("total_cached_tokens")),
        "output_tokens": first_value(agent.get("n_output_tokens"), metrics.get("total_completion_tokens")),
        "actual_cost_usd": first_value(agent.get("cost_usd"), metrics.get("total_cost_usd")),
        "usage_source": agent.get("usage_source") or result.get("usage_tracking", {}).get("usage_source"),
    }


def skill_names(skills_dir: Path) -> tuple[str | None, str | None]:
    """The frozen AB manifest is the authoritative A/B order for this task."""
    manifest = skills_dir.parent / "AB" / "manifest.json"
    if not manifest.exists():
        return None, None
    selected = read_json(manifest).get("selected_skills", [])
    return (selected[0] if len(selected) > 0 else None, selected[1] if len(selected) > 1 else None)


def event_tool_call(event: dict[str, Any]) -> dict[str, Any] | None:
    event_type = str(event.get("type") or event.get("event_type") or "")
    payload = event.get("tool_call") or event.get("toolCall") or event.get("tool") or {}
    if not isinstance(payload, dict):
        payload = {"value": payload}
    name = first_value(event.get("tool_name"), event.get("name") if "tool" in event_type.lower() else None,
                       payload.get("name"), payload.get("tool_name"))
    if "tool" not in event_type.lower() and name is None:
        return None
    return {"event_type": event_type, "tool_name": name, "arguments": payload.get("arguments") or event.get("arguments"), "raw": event}


def extract_trajectory(trajectory: Path | None, destination: Path, a_name: str | None, b_name: str | None) -> dict[str, Any]:
    """Preserve ACP JSONL and derive tool/skill evidence without inventing usage."""
    if trajectory is None:
        write_json(destination / "trajectory.json", {"source": None, "event_count": 0})
        write_json(destination / "tool_calls.json", [])
        return {"tool_calls": [], "skill_A_loaded": "unknown", "skill_B_loaded": "unknown", "skill_load_order": []}

    raw_dir = destination / "trajectory"
    raw_dir.mkdir(parents=True, exist_ok=True)
    raw_path = raw_dir / "acp_trajectory.jsonl"
    shutil.copy2(trajectory, raw_path)
    events: list[dict[str, Any]] = []
    for line in raw_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            event = json.loads(line)
            if isinstance(event, dict):
                events.append(event)
        except json.JSONDecodeError:
            continue

    calls: list[dict[str, Any]] = []
    evidence: list[str] = []
    for index, event in enumerate(events):
        call = event_tool_call(event)
        if call is not None:
            calls.append({"event_index": index, **call})
            text = json.dumps(call, ensure_ascii=False).lower()
            for name in (a_name, b_name):
                if name and name.lower() in text:
                    evidence.append(name)
        if "skill" in str(event.get("type") or event.get("event_type") or "").lower():
            text = json.dumps(event, ensure_ascii=False).lower()
            for name in (a_name, b_name):
                if name and name.lower() in text:
                    evidence.append(name)

    order = list(dict.fromkeys(evidence))
    write_json(destination / "trajectory.json", {"source": "trajectory/acp_trajectory.jsonl", "event_count": len(events), "tool_call_count": len(calls)})
    write_json(destination / "tool_calls.json", calls)
    return {"tool_calls": calls, "skill_A_loaded": True if a_name in order else "unknown", "skill_B_loaded": True if b_name in order else "unknown", "skill_load_order": order}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--task", required=True); parser.add_argument("--skills", required=True)
    parser.add_argument("--condition", required=True); parser.add_argument("--model", required=True)
    parser.add_argument("--run-dir", required=True); parser.add_argument("--pricing", required=True)
    args = parser.parse_args()
    base, key = os.environ.get("API_BASE_URL"), os.environ.get("API_KEY")
    if not base or not key:
        raise SystemExit("API_BASE_URL and API_KEY are required environment variables")
    run, task, skills = Path(args.run_dir), Path(args.task), Path(args.skills)
    if run.exists():
        raise SystemExit("run_dir must not exist; BenchFlow owns directory creation")
    env = os.environ.copy(); env["OPENAI_API_KEY"] = key; env["OPENAI_BASE_URL"] = base
    logical = os.environ.get("PILOT_MODEL", args.model)
    effective = os.environ.get("OPENCODE_EFFECTIVE_MODEL", f"openai/{logical}")
    cmd = [str(Path(sys.executable).parent / "bench"), "eval", "run", "--tasks-dir", str(task), "--agent", "opencode", "--model", effective, "--sandbox", "docker", "--skills-dir", str(skills), "--skill-mode", "no-skill" if args.condition == "ZERO" else "with-skill", "--usage-tracking", "required", "--jobs-dir", str(run), "--quiet"]
    started = now(); proc = subprocess.run(cmd, text=True, capture_output=True, env=env); child = rollout(run)
    if child:
        result = read_json(child / "result.json")
        source_trajectory = next(iter(child.rglob("acp_trajectory.jsonl")), None)
        verifier = next(iter(child.rglob("verifier/test-stdout.txt")), None)
        if child != run:
            shutil.copy2(child / "result.json", run / "result.json")
        a_name, b_name = skill_names(skills)
        evidence = extract_trajectory(source_trajectory, run, a_name, b_name)
        if verifier: shutil.copy2(verifier, run / "verifier.log")
        else: (run / "verifier.log").write_text("UNRESOLVED\n", encoding="utf-8")
        (run / "stdout.log").write_text(proc.stdout, encoding="utf-8"); (run / "stderr.log").write_text(proc.stderr, encoding="utf-8")
        usage = normalize_usage(result); write_json(run / "usage.json", usage)
        write_json(run / "metadata.json", {"timestamp_start": started, "timestamp_end": now(), "requested_model": logical, "effective_model_id": effective, "returned_model": result.get("model"), "provider": base, "condition": args.condition, "task": task.name, "skill_A_exposed": args.condition in {"A", "AB"}, "skill_B_exposed": args.condition in {"B", "AB"}, "skill_A_loaded": evidence["skill_A_loaded"], "skill_B_loaded": evidence["skill_B_loaded"], "skill_load_order": evidence["skill_load_order"], "api_call_count": result.get("agent_result", {}).get("n_prompts"), "retry_count": 0, "input_tokens": usage["input_tokens"], "cached_input_tokens": usage["cached_input_tokens"], "output_tokens": usage["output_tokens"], "actual_cost_usd": usage["actual_cost_usd"], "verifier_result": "PASS" if result.get("rewards", {}).get("reward") == 1 else "FAIL", "failure_type": result.get("error_category")})
    else:
        run.mkdir(parents=True); (run / "stdout.log").write_text(proc.stdout, encoding="utf-8"); (run / "stderr.log").write_text(proc.stderr, encoding="utf-8"); (run / "verifier.log").write_text("INFRASTRUCTURE_FAILURE\n", encoding="utf-8"); write_json(run / "trajectory.json", {"source": None, "event_count": 0}); write_json(run / "tool_calls.json", []); write_json(run / "usage.json", {"usage_available": False, "actual_cost_usd": None}); write_json(run / "result.json", {"verifier_result": "UNRESOLVED", "failure_type": "infrastructure_failure"}); write_json(run / "metadata.json", {"timestamp_start": started, "timestamp_end": now(), "requested_model": logical, "effective_model_id": effective, "provider": base, "condition": args.condition, "task": task.name, "skill_A_loaded": "unknown", "skill_B_loaded": "unknown", "failure_type": "infrastructure_failure", "infra_valid": False})
    raise SystemExit(proc.returncode)


if __name__ == "__main__":
    main()
