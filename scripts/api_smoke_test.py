"""NON_EXPERIMENTAL_API_SMOKE_TEST: delegates one non-experimental runner call."""
from pathlib import Path
import subprocess, sys
from common import ROOT
run=ROOT/"runs"/"smoke"/"NON_EXPERIMENTAL_API_SMOKE_TEST"
subprocess.run([sys.executable,str(ROOT/"scripts"/"run_agent.py"),"--task",str(ROOT/"sanitized_tasks"/"adaptive-cruise-control"),"--skills",str(ROOT/"conditions"/"adaptive-cruise-control"/"ZERO"),"--condition","ZERO","--model",__import__("os").environ["PILOT_MODEL"],"--run-dir",str(run),"--pricing",str(ROOT/"configs"/"pricing_snapshot.json")],check=True)
