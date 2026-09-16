from __future__ import annotations
import random
from common import CONDITIONS, dump, groups, rate, rows

def quantile(values,q): return values[max(0,min(len(values)-1,round(q*(len(values)-1))))]
def main():
    random.seed(20260915); g=groups(rows()); out=[]
    for task,model in sorted({x[:2] for x in g}):
        counts={c:rate(g.get((task,model,c),[])) for c in CONDITIONS}
        if any(n==0 for _,_,n in counts.values()): continue
        interactions=[]
        for _ in range(100000):
            p={c:random.betavariate(counts[c][1]+1, counts[c][2]-counts[c][1]+1) for c in CONDITIONS}
            interactions.append(p["AB"]-p["A"]-p["B"]+p["ZERO"])
        interactions.sort(); out.append({"task_id":task,"model":model,"posterior_mean_I":sum(interactions)/len(interactions),"ci95":[quantile(interactions,.025),quantile(interactions,.975)],"P_I_lt_0":sum(x<0 for x in interactions)/len(interactions)})
    dump("bayesian_interaction.json",out); print("Wrote reports/bayesian_interaction.json")
if __name__=="__main__": main()
