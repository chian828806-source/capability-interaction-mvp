"""Offline phase-to-runner hand-off test; it deliberately makes no API call."""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
phase_source = (ROOT / "scripts" / "run_phase.py").read_text(encoding="utf-8")

# The phase owns planning metadata only.  BenchFlow, invoked by run_agent, owns
# creation of the jobs directory.  Keep this source-level assertion close to the
# executable boundary so a future eager mkdir is caught before an API run.
assert 'run_dir = ROOT / "runs" / "raw" / run_id' in phase_source
assert 'run_dir.mkdir(parents=True, exist_ok=False)' not in phase_source

with tempfile.TemporaryDirectory() as temp:
    root = Path(temp)
    task = root / "task"; skills = root / "skills"; run_dir = root / "benchflow-jobs"
    task.mkdir(); skills.mkdir()
    assert not run_dir.exists()
    env = os.environ.copy()
    env.pop("API_BASE_URL", None); env.pop("API_KEY", None)
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "run_agent.py"),
         "--task", str(task), "--skills", str(skills), "--condition", "ZERO",
         "--model", "logical-model", "--run-dir", str(run_dir),
         "--pricing", str(ROOT / "configs" / "pricing_snapshot.json")],
        cwd=ROOT, text=True, capture_output=True, env=env, check=False,
    )
    # Missing credentials is intentionally the first failure after the runner
    # accepts the phase hand-off.  In particular it must not report a preexisting
    # jobs directory, nor create one before BenchFlow is started.
    assert "API_BASE_URL and API_KEY" in result.stderr
    assert "run_dir must not exist" not in result.stderr
    assert not run_dir.exists()

print("phase-to-runner-run-dir-integration-pass")
