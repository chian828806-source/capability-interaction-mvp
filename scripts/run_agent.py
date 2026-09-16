"""OpenAI-compatible, append-only agent runner for one frozen experiment run."""
from __future__ import annotations
import argparse, json, os, time, urllib.error, urllib.request
from pathlib import Path
from common import now, read_json, write_json

AGENT_FAILURES = {"agent_timeout", "max_steps", "max_api_calls"}

def price(usage: dict, pricing: dict) -> dict:
    if not any(k in usage for k in ("prompt_tokens", "input_tokens", "completion_tokens", "output_tokens")):
        raise RuntimeError("usage missing; cost must fail closed")
    inp = int(usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0); cached = int(usage.get("cached_input_tokens", 0) or 0)
    out = int(usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0)
    cost = (inp-cached)*pricing["input_price_per_1M"]/1e6 + cached*(pricing.get("cached_input_price_per_1M") or pricing["input_price_per_1M"])/1e6 + out*pricing["output_price_per_1M"]/1e6
    return {"input_tokens": inp, "cached_input_tokens": cached, "output_tokens": out, "actual_cost_usd": cost}

def main() -> None:
    p=argparse.ArgumentParser(); p.add_argument("--task", required=True); p.add_argument("--skills", required=True); p.add_argument("--condition", required=True); p.add_argument("--model", required=True); p.add_argument("--run-dir", required=True); p.add_argument("--pricing", required=True); args=p.parse_args()
    base,key=os.environ.get("API_BASE_URL"),os.environ.get("API_KEY")
    if not base or not key: raise SystemExit("API_BASE_URL and API_KEY are required environment variables")
    run=Path(args.run_dir); run.mkdir(parents=True, exist_ok=False); skills=Path(args.skills); task=Path(args.task)
    exposed=sorted(x.name for x in skills.iterdir() if x.is_dir()); spec=read_json(Path(args.pricing))
    prompt=(task/"task.md").read_text(encoding="utf-8", errors="replace")+"\n\nAvailable skills: "+", ".join(exposed)
    meta={"timestamp_start":now(),"requested_model":args.model,"provider":base,"condition":args.condition,"task":task.name,"skill_A_exposed":len(exposed)>0 and args.condition in {"A","AB"},"skill_B_exposed":len(exposed)>0 and args.condition in {"B","AB"},"skill_A_loaded":False,"skill_B_loaded":False,"skill_load_order":[],"api_call_count":0,"retry_count":0}
    write_json(run/"metadata.json",meta); write_json(run/"tool_calls.json",[]); write_json(run/"trajectory.json",[{"event":"start","time":now()}])
    payload={"model":os.environ.get("PILOT_MODEL",args.model),"messages":[{"role":"user","content":prompt}],"max_tokens":4096}
    req=urllib.request.Request(base.rstrip("/")+"/chat/completions",data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
    try:
        meta["api_call_count"]+=1; started=time.monotonic()
        with urllib.request.urlopen(req,timeout=1800) as response: raw=json.loads(response.read())
        usage=price(raw.get("usage",{}),spec["models"][args.model]); returned=raw.get("model",args.model)
        write_json(run/"usage.json",usage); write_json(run/"result.json",{"requested_model":args.model,"returned_model":returned,"provider":base,"condition":args.condition,"task":task.name,"verifier_result":"UNRESOLVED","failure_type":None,**usage})
        (run/"verifier.log").write_text("UNRESOLVED: runner does not alter or execute benchmark verifier.\n",encoding="utf-8")
        (run/"stdout.log").write_text(json.dumps(raw),encoding="utf-8"); (run/"stderr.log").write_text("",encoding="utf-8")
        meta.update({"timestamp_end":now(),"returned_model":returned,"wall_time":time.monotonic()-started,"failure_type":None,**usage})
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        (run/"stdout.log").write_text("",encoding="utf-8"); (run/"stderr.log").write_text(str(exc),encoding="utf-8"); (run/"verifier.log").write_text("INFRASTRUCTURE_FAILURE\n",encoding="utf-8")
        write_json(run/"usage.json",{"usage_available":False,"actual_cost_usd":None}); write_json(run/"result.json",{"requested_model":args.model,"returned_model":None,"provider":base,"condition":args.condition,"task":task.name,"verifier_result":"UNRESOLVED","failure_type":"infrastructure_network_failure"})
        meta.update({"timestamp_end":now(),"failure_type":"infrastructure_network_failure","infra_valid":False})
    write_json(run/"metadata.json",meta)
if __name__ == "__main__": main()
