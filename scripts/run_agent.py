"""Real BenchFlow/OpenCode ACP runner; never implements a chat-completion loop."""
from __future__ import annotations
import argparse, json, os, shutil, subprocess, sys
from pathlib import Path
from common import now, read_json, write_json

def rollout(root: Path) -> Path | None:
    found=sorted(root.rglob("result.json"),key=lambda p:p.stat().st_mtime)
    return found[-1].parent if found else None

def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--task", required=True); p.add_argument("--skills", required=True); p.add_argument("--condition", required=True); p.add_argument("--model", required=True); p.add_argument("--run-dir", required=True); p.add_argument("--pricing", required=True); args=p.parse_args()
    base,key=os.environ.get("API_BASE_URL"),os.environ.get("API_KEY")
    if not base or not key: raise SystemExit("API_BASE_URL and API_KEY are required environment variables")
    run=Path(args.run_dir); task=Path(args.task); skills=Path(args.skills)
    if run.exists(): raise SystemExit("run_dir must not exist; BenchFlow owns directory creation")
    env=os.environ.copy(); env["OPENAI_API_KEY"]=key; env["OPENAI_BASE_URL"]=base
    logical=os.environ.get("PILOT_MODEL",args.model); effective=os.environ.get("OPENCODE_EFFECTIVE_MODEL",f"openai/{logical}")
    cmd=[str(Path(sys.executable).parent/"bench"),"eval","run","--tasks-dir",str(task),"--agent","opencode","--model",effective,"--sandbox","docker","--skills-dir",str(skills),"--skill-mode","no-skill" if args.condition=="ZERO" else "with-skill","--usage-tracking","required","--jobs-dir",str(run),"--quiet"]
    started=now(); proc=subprocess.run(cmd,text=True,capture_output=True,env=env); child=rollout(run)
    if child:
        result=read_json(child/"result.json"); trajectory=next(iter(child.rglob("*trajectory*.jsonl")),None); verifier=next(iter(child.rglob("verifier/test-stdout.txt")),None)
        if trajectory: shutil.copy2(trajectory,run/"trajectory.json")
        else: write_json(run/"trajectory.json",[])
        shutil.copy2(child/"result.json",run/"result.json"); (run/"tool_calls.json").write_text("[]\n",encoding="utf-8")
        if verifier: shutil.copy2(verifier,run/"verifier.log")
        else: (run/"verifier.log").write_text("UNRESOLVED\n",encoding="utf-8")
        (run/"stdout.log").write_text(proc.stdout,encoding="utf-8"); (run/"stderr.log").write_text(proc.stderr,encoding="utf-8")
        usage={**result.get("agent_result",{}),**result.get("final_metrics",{})}; write_json(run/"usage.json",usage)
        write_json(run/"metadata.json",{"timestamp_start":started,"timestamp_end":now(),"requested_model":logical,"effective_model_id":effective,"returned_model":result.get("model"),"provider":base,"condition":args.condition,"task":task.name,"skill_A_exposed":args.condition in {"A","AB"},"skill_B_exposed":args.condition in {"B","AB"},"skill_A_loaded":None,"skill_B_loaded":None,"skill_load_order":[],"api_call_count":result.get("agent_result",{}).get("n_prompts"),"retry_count":0,"verifier_result":"PASS" if result.get("rewards",{}).get("reward")==1 else "FAIL","failure_type":result.get("error_category")})
    else:
        run.mkdir(parents=True); (run/"stdout.log").write_text(proc.stdout,encoding="utf-8"); (run/"stderr.log").write_text(proc.stderr,encoding="utf-8"); (run/"verifier.log").write_text("INFRASTRUCTURE_FAILURE\n",encoding="utf-8"); write_json(run/"trajectory.json",[]); write_json(run/"tool_calls.json",[]); write_json(run/"usage.json",{"usage_available":False,"actual_cost_usd":None}); write_json(run/"result.json",{"verifier_result":"UNRESOLVED","failure_type":"infrastructure_failure"}); write_json(run/"metadata.json",{"timestamp_start":started,"timestamp_end":now(),"requested_model":logical,"effective_model_id":effective,"provider":base,"condition":args.condition,"task":task.name,"failure_type":"infrastructure_failure","infra_valid":False})
    raise SystemExit(proc.returncode)
if __name__ == "__main__": main()
