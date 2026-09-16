from __future__ import annotations
from statistics import mean
from common import dump, groups, rows
def number(x):
    try:return float(x)
    except (TypeError,ValueError):return None
def main():
    out=[]
    for (task,model,condition),rs in sorted(groups(rows()).items()):
        item={"task_id":task,"model":model,"condition":condition,"n":len(rs)}
        for source,target in [("estimated_cost_usd","avg_cost_usd"),("input_tokens","avg_input_tokens"),("output_tokens","avg_output_tokens"),("number_of_api_calls","avg_api_calls"),("tool_calls","avg_tool_calls")]:
            values=[number(r.get(source)) for r in rs]; values=[v for v in values if v is not None]; item[target]=mean(values) if values else None
        out.append(item)
    dump("cost_analysis.json",out); print("Wrote reports/cost_analysis.json")
if __name__=="__main__": main()
