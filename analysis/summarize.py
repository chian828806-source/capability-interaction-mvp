from __future__ import annotations
import csv
from common import ROOT, groups, rate, rows, wilson

def main():
    output=[]
    for (task, model, condition), record in sorted(groups(rows()).items()):
        p,k,n=rate(record); lo,hi=wilson(k,n)
        output.append({"task_id":task,"model":model,"condition":condition,"success":k,"n":n,"pass_rate":p,"wilson_low":lo,"wilson_high":hi,
            "skill_A_loaded_rate":sum(str(x.get("skill_A_loaded")).lower()=="true" for x in record)/n,
            "skill_B_loaded_rate":sum(str(x.get("skill_B_loaded")).lower()=="true" for x in record)/n})
    path=ROOT/"reports"/"summary.csv"; path.parent.mkdir(exist_ok=True)
    with path.open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=output[0].keys() if output else ["task_id","model","condition","success","n","pass_rate","wilson_low","wilson_high","skill_A_loaded_rate","skill_B_loaded_rate"]); w.writeheader(); w.writerows(output)
    print(f"Wrote {path}")
if __name__=="__main__": main()
