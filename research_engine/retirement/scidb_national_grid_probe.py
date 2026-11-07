#!/usr/bin/env python3
"""Inventory the actual ScienceDB historical 1km climate raster tree."""
from __future__ import annotations
import json,hashlib,urllib.request,datetime,pathlib,sys
DATASET_ID="cece16f1863b4ebd839894f6df26f8ac"
VERSION="V8"
API="https://www.scidb.cn/api/gin-sdb-filetree/public/file/childrenFileListByPath"
OUT=pathlib.Path("research_engine/retirement/output/scidb_national_grid_probe.json")

def post(path,last=0):
    payload={"dataSetId":DATASET_ID,"version":VERSION,"path":path,"lastIndex":last,"pageSize":200}
    req=urllib.request.Request(API,data=json.dumps(payload).encode(),
      headers={"Content-Type":"application/json","User-Agent":"RetirementClimateResearch/1.0"})
    with urllib.request.urlopen(req,timeout=60) as r:
      raw=r.read(); d=json.loads(raw)
    if d.get("code")!=20000 or not isinstance(d.get("data"),list):
      raise RuntimeError("ScienceDB API error: "+repr(d)[:1200])
    return raw,d["data"]

def main():
  result={"schema":"RET_SCIDB_CHINA_1KM_CLIMATE_ACCESS_PROBE_V2","dataset_id":DATASET_ID,
    "version":VERSION,"tested_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
    "endpoint":API,"formal_valid_county_screenings":0,"county_exclusions":0,"directory_results":[],
    "files":[],"errors":[]}
  queue=["/V8","/V8/history_data"]
  seen=set()
  while queue and len(seen)<100:
    p=queue.pop(0)
    if p in seen: continue
    seen.add(p)
    try:
      raw,items=post(p)
      result["directory_results"].append({"path":p,"http_status":200,"response_sha256":hashlib.sha256(raw).hexdigest(),"count":len(items)})
      for x in items:
        if not isinstance(x,dict): continue
        row={k:x.get(k) for k in ["id","fileName","name","path","size","type","isFolder","fileType"] if k in x}
        row["parent_path"]=p
        size=int(x.get("size") or 0)
        fname=str(x.get("fileName") or "")
        child=str(x.get("path") or "")
        isfolder=(size==0 and child and not fname.lower().endswith((".tif",".tiff",".zip",".rar",".7z",".docx",".pdf",".txt",".csv",".r",".py")))
        if isfolder and child not in seen: queue.append(child)
        else: result["files"].append(row)
    except Exception as e:
      result["errors"].append({"path":p,"error_type":type(e).__name__,"error":str(e)[:800]})
  result["directories_scanned"]=len(seen)
  result["file_count"]=len(result["files"])
  result["total_listed_bytes"]=sum(int(x.get("size") or 0) for x in result["files"])
  result["historical_variable_matches"]={v:[x for x in result["files"] if v.lower() in str(x.get("fileName","")).lower()] for v in ["tasmax","tasmin","tas","pr","sunp"]}
  result["status"]="HISTORY_FILE_INVENTORY_PASS" if result["historical_variable_matches"]["tasmax"] and result["historical_variable_matches"]["sunp"] else "HISTORY_FILE_INVENTORY_INCOMPLETE"
  OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  print(json.dumps({k:v for k,v in result.items() if k not in ["files","historical_variable_matches"]},ensure_ascii=False))
  print("VARIABLE_FILES",json.dumps({k:[{z:f.get(z) for z in ["fileName","size","id","path"]} for f in v] for k,v in result["historical_variable_matches"].items()},ensure_ascii=False)[:16000])
  if result["status"]!="HISTORY_FILE_INVENTORY_PASS": sys.exit(2)
if __name__=="__main__": main()
