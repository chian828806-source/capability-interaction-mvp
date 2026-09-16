from __future__ import annotations
from common import dump, groups, rows
def truth(v): return str(v).lower()=="true"
def main():
    out=[]
    for (task,model,condition), rs in sorted(groups(rows()).items()):
        n=len(rs); out.append({"task_id":task,"model":model,"condition":condition,"n":n,"A_load_rate":sum(truth(x.get("skill_A_loaded")) for x in rs)/n,"B_load_rate":sum(truth(x.get("skill_B_loaded")) for x in rs)/n,"both_load_rate":sum(truth(x.get("skill_A_loaded")) and truth(x.get("skill_B_loaded")) for x in rs)/n})
    dump("utilization.json",out); print("Wrote reports/utilization.json")
if __name__=="__main__": main()
