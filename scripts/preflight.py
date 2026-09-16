"""Generate the mandatory preflight report without making model calls."""
from __future__ import annotations
from pathlib import Path
from common import ROOT, read_json, sha256_file

def yes(value): return "PASS" if value else "BLOCKED"

def main():
    pre=read_json(ROOT/"preregistration.yaml"); env=ROOT/"environment_manifest.json"; pricing=read_json(ROOT/"configs"/"pricing_snapshot.json")
    audits=[]
    for task in pre["tasks"]:
        path=ROOT/"task_audit"/f"{task}.json"; audits.append((task,read_json(path).get("eligible") if path.exists() else False))
    isolation=ROOT/"reports"/"ISOLATION_REPORT.json"; isolated=isolation.exists() and read_json(isolation).get("pass")
    price_ready=bool(pricing.get("date") and pricing.get("source"))
    lines=["# MVP Preflight Report", "", "## Status", "", f"- Qualification audits: {yes(all(v for _,v in audits))}", f"- No-skill isolation: {yes(isolated)}", f"- Environment manifest: {yes(env.exists())}", f"- Same-day pricing snapshot: {yes(price_ready)}", f"- Formal configuration hash: `{sha256_file(ROOT/'configs'/'experiment.yaml')}`", f"- Preregistration hash: `{sha256_file(ROOT/'preregistration.yaml')}`", "", "## Fixed benchmark and model plan", "", "- SkillsBench: `v1.1` / `b63b7b2`", "- BenchFlow: `>=0.6.4,<0.7` (see `PROTOCOL_DEVIATIONS.md` for public-release compatibility note)", "- Pilot: `gpt-5.4-nano-2026-03-17`", "- Screening/confirmation: `gpt-5.4-mini-2026-03-17`", "- Conditional replication: `gemini-3.8-flash`", "- Provider: `302.AI`, with automatic routing disabled", "- Total budget cap: `$15.00`", "", "## Task audits", ""]
    lines += [f"- `{task}`: {yes(ok)}" for task,ok in audits]
    lines += ["", "## Required action before Pilot", "", "Do not start a paid run until all items in Status are PASS, API credentials are present only in environment variables, and the fixed provider-agnostic harness command has been reviewed.  Any failed audit makes the associated task ineligible; Task 2 must then follow the preregistered backup selection rule.", ""]
    (ROOT/"reports"/"PREFLIGHT_REPORT.md").write_text("\n".join(lines),encoding="utf-8")
    print("Wrote reports/PREFLIGHT_REPORT.md")
if __name__=="__main__": main()
