from __future__ import annotations
from common import CONDITIONS, dump, groups, rate, rows

def main():
    all_groups=groups(rows()); output=[]
    keys=sorted({k[:2] for k in all_groups})
    for task,model in keys:
        values={c:rate(all_groups.get((task,model,c),[]))[0] for c in CONDITIONS}
        if any(v is None for v in values.values()): continue
        da=values["A"]-values["ZERO"]; db=values["B"]-values["ZERO"]; interaction=values["AB"]-values["A"]-values["B"]+values["ZERO"]
        candidate=da>=.2 and db>=.2 and values["AB"]<=min(values["A"],values["B"])-.2 and interaction<0
        output.append({"task_id":task,"model":model,"p":values,"delta_A":da,"delta_B":db,"I_AB":interaction,"negative_candidate":candidate})
    dump("interaction.json",output); print("Wrote reports/interaction.json")
if __name__=="__main__": main()
