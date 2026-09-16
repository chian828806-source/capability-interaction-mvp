"""Local/mock runner integration test; no API, Docker, or benchmark mutation."""
import os, sys, tempfile
from pathlib import Path
from types import SimpleNamespace
import run_agent

with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp); task=root/"task"; skills=root/"skills"; task.mkdir(); skills.mkdir(); (task/"task.md").write_text("mock")
    (skills/"skill-a").mkdir(); out=root/"run"
    old=sys.argv; sys.argv=["run_agent.py","--task",str(task),"--skills",str(skills),"--condition","A","--model","mock","--run-dir",str(out),"--pricing",str(root/"prices.json")]
    oldrun=run_agent.subprocess.run; os.environ["API_BASE_URL"]="http://mock"; os.environ["API_KEY"]="mock"
    def fake(cmd, **kwargs):
        child=out/"mock"/"rollout"; (child/"verifier").mkdir(parents=True); (child/"result.json").write_text('{"rewards":{"reward":1},"agent_result":{"n_prompts":1}}'); (child/"verifier"/"test-stdout.txt").write_text("PASS")
        return SimpleNamespace(returncode=0,stdout="mock",stderr="")
    run_agent.subprocess.run=fake
    try:
        try: run_agent.main()
        except SystemExit as exc: assert exc.code==0
        assert all((out/name).exists() for name in ("trajectory.json","result.json","usage.json","tool_calls.json","verifier.log","stdout.log","stderr.log","metadata.json"))
    finally: run_agent.subprocess.run=oldrun; sys.argv=old
print("mock-runner-integration-pass")
