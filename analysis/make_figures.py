"""Create dependency-free SVG figures from derived data; no figures imply no evidence."""
from __future__ import annotations
import csv, json
from pathlib import Path
from common import ROOT

def main():
    summary=ROOT/"reports"/"summary.csv"
    if not summary.exists(): raise SystemExit("Run summarize.py first.")
    with summary.open(encoding="utf-8",newline="") as f: rows=list(csv.DictReader(f))
    for key in sorted({(r["task_id"],r["model"]) for r in rows}):
        part={r["condition"]:r for r in rows if (r["task_id"],r["model"])==key}; labels=["ZERO","A","B","AB"]
        bars=[]
        for i,label in enumerate(labels):
            rate=float(part.get(label,{}).get("pass_rate") or 0); x=70+i*120; y=330-rate*260
            bars.append(f'<rect x="{x}" y="{y:.1f}" width="64" height="{rate*260:.1f}" fill="#2f6f9f"/><text x="{x+32}" y="355" text-anchor="middle">{label}</text><text x="{x+32}" y="{y-7:.1f}" text-anchor="middle">{rate:.2f}</text>')
        safe="_".join(key).replace("/","_")
        svg=f'<svg xmlns="http://www.w3.org/2000/svg" width="600" height="390"><style>text{{font:14px sans-serif}} .t{{font-weight:bold;font-size:16px}}</style><text class="t" x="20" y="25">Pass rate: {key[0]} / {key[1]}</text><line x1="50" y1="330" x2="560" y2="330" stroke="black"/><line x1="50" y1="70" x2="50" y2="330" stroke="black"/>{"".join(bars)}</svg>'
        (ROOT/"figures"/f"pass_rate_{safe}.svg").write_text(svg,encoding="utf-8")
    interaction=ROOT/"reports"/"interaction.json"
    if interaction.exists():
        data=json.loads(interaction.read_text(encoding="utf-8")); (ROOT/"figures"/"interaction_contrast.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")
    print("Wrote figures.")
if __name__=="__main__": main()
