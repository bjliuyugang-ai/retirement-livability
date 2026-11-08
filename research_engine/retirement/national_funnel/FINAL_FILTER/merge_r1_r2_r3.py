#!/usr/bin/env python3
"""Merge immutable R1 results with R2 winter and R3 summer climate metrics."""
from __future__ import annotations
import csv
import datetime as dt
import json
import os
import pathlib

ROOT=pathlib.Path("research_engine/retirement/national_funnel")
R1_POINTER=ROOT/"R1"/"output"/"R1_LATEST.json"
CLIMATE_DIR=ROOT/"R2_R3_CLIMATE"/"output"
OUT_ROOT=ROOT/"FINAL_FILTER"/"runs"
RUN_ID=os.getenv("GITHUB_RUN_ID","MANUAL")

def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()

def read_json(p):
    return json.loads(p.read_text(encoding="utf-8-sig"))

def read_csv(p):
    with p.open(encoding="utf-8-sig",newline="") as f:
        return list(csv.DictReader(f))

def write_csv(p,rows):
    p.parent.mkdir(parents=True,exist_ok=True)
    fields=[]
    for row in rows:
        for k in row:
            if k not in fields: fields.append(k)
    with p.open("w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

def main():
    pointer=read_json(R1_POINTER)
    r1_dir=pathlib.Path(pointer["run_directory"])
    r1_rows=read_csv(r1_dir/"R1_REMAINING.csv")
    climate_rows=read_csv(CLIMATE_DIR/"R2_R3_CLIMATE_METRICS_ALL_2847.csv")
    climate={str(x["code"]):x for x in climate_rows}
    merged=[]
    for row in r1_rows:
        code=str(row["code"])
        c=climate.get(code)
        out=dict(row)
        if c is None:
            out.update({"climate_match_status":"MISSING","winter_status":"PENDING","summer_status":"PENDING"})
        else:
            out.update(c)
            out["climate_match_status"]="MATCH"
        merged.append(out)
    if len(merged)!=int(pointer["remaining_count"]):
        raise RuntimeError(f"R1_REMAINING_COUNT_MISMATCH expected={pointer['remaining_count']} actual={len(merged)}")
    r2_excluded=[x for x in merged if x.get("winter_status")=="EXCLUDE"]
    r2_carry=[x for x in merged if x.get("winter_status")!="EXCLUDE"]
    r3_excluded=[x for x in r2_carry if x.get("summer_status")=="EXCLUDE"]
    final_carry=[x for x in r2_carry if x.get("summer_status")!="EXCLUDE"]
    out_dir=OUT_ROOT/RUN_ID
    out_dir.mkdir(parents=True,exist_ok=True)
    write_csv(out_dir/"R2_AFTER_R1_WINTER_EXCLUDED.csv",r2_excluded)
    write_csv(out_dir/"R2_AFTER_R1_WINTER_CARRY_FORWARD.csv",r2_carry)
    write_csv(out_dir/"R3_AFTER_R1_R2_SUMMER_EXCLUDED.csv",r3_excluded)
    write_csv(out_dir/"FINAL_CARRY_FORWARD_AFTER_R1_R2_R3.csv",final_carry)
    summary={
      "schema":"RETIREMENT_NATIONAL_FUNNEL_R1_R2_R3_MERGED_V1",
      "status":"COMPLETED_WITH_PENDING",
      "created_at_utc":now(),
      "r1_run_id":pointer["latest_run_id"],
      "merge_run_id":RUN_ID,
      "r1_input_count":int(pointer["input_count"]),
      "r1_excluded_count":int(pointer["excluded_count"]),
      "r1_remaining_count":len(merged),
      "r2_winter":{
        "excluded_count":len(r2_excluded),
        "carry_forward_count":len(r2_carry),
        "pending_count":sum(x.get("winter_status")=="PENDING" for x in r2_carry)
      },
      "r3_summer_after_r2":{
        "excluded_count":len(r3_excluded),
        "final_carry_forward_count":len(final_carry),
        "pending_count":sum(x.get("summer_status")=="PENDING" for x in final_carry)
      },
      "final_count_after_three_climate_batches":len(final_carry),
      "climate_data_source":"CHM_Tmax v2, 0.1-degree daily Tmax, 1991-2020",
      "screening_policy":"R2 and R3 statuses are conservative county-area first-pass screens. Pending units carry forward; no missing metric is treated as a failure.",
      "files":{
        "r2_excluded":"R2_AFTER_R1_WINTER_EXCLUDED.csv",
        "r2_carry":"R2_AFTER_R1_WINTER_CARRY_FORWARD.csv",
        "r3_excluded":"R3_AFTER_R1_R2_SUMMER_EXCLUDED.csv",
        "final_carry":"FINAL_CARRY_FORWARD_AFTER_R1_R2_R3.csv"
      }
    }
    (out_dir/"FINAL_STAGE1_3_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    pointer_out={
      "schema":"RETIREMENT_FINAL_FILTER_LATEST_POINTER_V1",
      "merge_run_id":RUN_ID,
      "r1_run_id":pointer["latest_run_id"],
      "run_directory":str(out_dir),
      "final_count":len(final_carry),
      "summary_file":"FINAL_STAGE1_3_SUMMARY.json"
    }
    latest=ROOT/"FINAL_FILTER"/"FINAL_LATEST.json"
    latest.parent.mkdir(parents=True,exist_ok=True)
    latest.write_text(json.dumps(pointer_out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False),flush=True)

if __name__=="__main__":
    main()
