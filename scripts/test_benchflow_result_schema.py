"""Synthetic BenchFlow 0.6.7 artifact test; never calls an API or Docker."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import run_agent
from run_phase import actual_cost
from common import read_json, write_json


result = {
    "agent_result": {"n_input_tokens": 120, "n_output_tokens": 30,
                     "n_cache_read_tokens": 20, "cost_usd": 0.01234,
                     "usage_source": "provider"},
    "final_metrics": {"total_prompt_tokens": 999, "total_completion_tokens": 999,
                      "total_cached_tokens": 999, "total_cost_usd": 9.99},
}
usage = run_agent.normalize_usage(result)
assert usage == {"input_tokens": 120, "cached_input_tokens": 20, "output_tokens": 30,
                 "actual_cost_usd": 0.01234, "usage_source": "provider"}

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary); raw = root / "acp_trajectory.jsonl"; out = root / "out"
    raw.write_text(
        json.dumps({"type": "tool_call", "tool_name": "read_file", "arguments": {"path": "/skills/vehicle-dynamics/SKILL.md"}}) + "\n" +
        json.dumps({"type": "tool_call", "tool_name": "read_file", "arguments": {"path": "/skills/pid-controller/SKILL.md"}}) + "\n",
        encoding="utf-8")
    evidence = run_agent.extract_trajectory(raw, out, "vehicle-dynamics", "pid-controller")
    assert evidence["skill_A_loaded"] is True and evidence["skill_B_loaded"] is True
    assert evidence["skill_load_order"] == ["vehicle-dynamics", "pid-controller"]
    assert len(read_json(out / "tool_calls.json")) == 2
    assert (out / "trajectory" / "acp_trajectory.jsonl").read_text(encoding="utf-8") == raw.read_text(encoding="utf-8")
    assert read_json(out / "trajectory.json")["source"] == "trajectory/acp_trajectory.jsonl"

    write_json(out / "usage.json", usage)
    prices = {"input_price_per_1M": 10, "cached_input_price_per_1M": 1, "output_price_per_1M": 20}
    assert actual_cost(out, prices)["actual_cost_usd"] == 0.01234
    write_json(out / "usage.json", {"input_tokens": 120, "cached_input_tokens": 20, "output_tokens": 30, "actual_cost_usd": None})
    assert actual_cost(out, prices)["actual_cost_usd"] == 0.00162
    write_json(out / "usage.json", {"input_tokens": None, "cached_input_tokens": 0, "output_tokens": 0})
    try:
        actual_cost(out, prices)
        raise AssertionError("missing usage must fail closed")
    except RuntimeError:
        pass

print("synthetic-benchflow-result-schema-pass")
