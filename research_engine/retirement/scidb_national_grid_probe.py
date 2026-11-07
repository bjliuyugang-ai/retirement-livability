#!/usr/bin/env python3
"""Probe ScienceDB public file-tree API for the China 1 km 1991-2020 climate dataset.

This is a source-access test only. It does not create county screenings or exclusions.
"""
from __future__ import annotations
import json, hashlib, urllib.request, urllib.error, datetime, os, pathlib, sys

DATASET_ID = "cece16f1863b4ebd839894f6df26f8ac"
API = "https://www.scidb.cn/api/gin-sdb-filetree/public/file/childrenFileListByPath"
OUT = pathlib.Path("research_engine/retirement/output/scidb_national_grid_probe.json")
VERSIONS = ["V8", "V7", "V6", "V5", "V4", "V3", "V2", "V1"]

def post(payload):
    req=urllib.request.Request(API,data=json.dumps(payload).encode(),
      headers={"Content-Type":"application/json","User-Agent":"RetirementClimateResearch/1.0"})
    with urllib.request.urlopen(req,timeout=45) as r:
        raw=r.read()
        return r.status,raw,json.loads(raw)

def main():
    result={"schema":"RET_SCIDB_CHINA_1KM_CLIMATE_ACCESS_PROBE_V1",
      "dataset_id":DATASET_ID,"tested_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
      "endpoint":API,"formal_valid_county_screenings":0,"county_exclusions":0,"attempts":[]}
    success=None
    for version in VERSIONS:
      for folder in ["/",f"/{version}"]:
        payload={"dataSetId":DATASET_ID,"version":version,"path":folder,"lastIndex":0,"pageSize":100}
        try:
          status,raw,data=post(payload)
          row={"version":version,"path":folder,"http_status":status,
               "response_sha256":hashlib.sha256(raw).hexdigest(),"response_bytes":len(raw),
               "api_code":data.get("code"),"message":data.get("message"),
               "data_type":type(data.get("data")).__name__}
          if data.get("code")==20000 and isinstance(data.get("data"),list):
            row["items"]=[{k:x.get(k) for k in ["id","fileName","name","path","size","type","isFolder","fileType"] if k in x}
                          for x in data["data"][:100] if isinstance(x,dict)]
            result["attempts"].append(row)
            if data["data"]:
              success={"version":version,"path":folder,"items":data["data"]}
              break
          else:
            row["response_preview"]=raw[:1000].decode("utf-8","replace")
            result["attempts"].append(row)
        except Exception as e:
          result["attempts"].append({"version":version,"path":folder,"error_type":type(e).__name__,"error":str(e)[:1000]})
      if success: break
    if success:
      result["status"]="FILE_TREE_ACCESS_PASS"
      result["working_version"]=success["version"]
      result["working_path"]=success["path"]
      result["root_items"]=[{k:x.get(k) for k in ["id","fileName","name","path","size","type","isFolder","fileType"] if k in x}
                            for x in success["items"] if isinstance(x,dict)]
    else:
      result["status"]="FILE_TREE_ACCESS_BLOCKED_OR_VERSION_PATH_UNKNOWN"
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in result.items() if k!="attempts"},ensure_ascii=False))
    print(json.dumps(result["attempts"],ensure_ascii=False)[:12000])
    if not success: sys.exit(2)

if __name__=="__main__": main()
