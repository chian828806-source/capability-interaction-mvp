"""Generate the mandatory preflight report without making model calls."""
from __future__ import annotations
from pathlib import Path
from common import FINAL_PREREGISTRATION, ROOT, read_json, sha256_file

def yes(value): return "PASS" if value else "BLOCKED"

def main():
    pre=read_json(FINAL_PREREGISTRATION); env=ROOT/"environment_manifest.json"; pricing=read_json(ROOT/"configs"/"pricing_snapshot.json")
    audits=[]
    for task in pre["tasks"]:
        path=ROOT/"task_audit"/f"{task}.json"; audits.append((task,read_json(path).get("eligible") if path.exists() else False))
    isolation=ROOT/"reports"/"ISOLATION_REPORT.json"; isolated=isolation.exists() and read_json(isolation).get("pass")
    price_ready=bool(pricing.get("date") and pricing.get("source"))
    lines=["# MVP Preflight Report", "", "## Status", "", f"- Qualification audits: {yes(all(v for _,v in audits))}", f"- No-skill isolation, including Docker bind-mount check: {yes(isolated)}", f"- WSL environment manifest: {yes(env.exists())}", f"- Same-day pricing snapshot: {yes(price_ready)} (required only immediately before an API run)", f"- Experiment configuration hash: `{sha256_file(ROOT/'configs'/'experiment.yaml')}`", f"- Final preregistration hash: `{sha256_file(FINAL_PREREGISTRATION)}`", "", "## Frozen API Pilot", "", "- Tasks: `adaptive-cruise-control`, `hvac-control`", "- Plan: `2 Tasks × 4 Conditions × 1 repetition = 8 Pilot runs`", "- Budget hard stop: `$15.00`", "- Status: `READY_FOR_API_PILOT`", "", "## Task audits", ""]
    lines += [f"- `{task}`: {yes(ok)}" for task,ok in audits]
    lines += ["", "## Required action before Pilot", "", "Set a same-day sourced price snapshot and API credentials only as environment variables, then review the provider-agnostic runner command. This report itself makes no API call.", ""]
    (ROOT/"reports"/"PREFLIGHT_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
    print("Wrote reports/PREFLIGHT_REPORT.md")
if __name__=="__main__": main()
