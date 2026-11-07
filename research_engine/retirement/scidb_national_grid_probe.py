#!/usr/bin/env python3
"""Download and inspect the historical 1km Tmax and sunshine-percent rasters."""
from __future__ import annotations
import json,hashlib,urllib.request,datetime,pathlib,zipfile,io,sys,os
DATASET_ID="cece16f1863b4ebd839894f6df26f8ac"
FILES={
 "tasmax":{"id":"dba1c67431a07f5c3a7d18a83bd876d2","name":"China_tasmax_1km_1991-2020.zip","expected":293775088},
 "sunp":{"id":"cc20e819b4c903a1dc200aeead645e7c","name":"China_sunp_1km_1991-2020.zip","expected":286802207}
}
BASE=pathlib.Path("research_engine/retirement/output/scidb_download")
OUT=pathlib.Path("research_engine/retirement/output/scidb_national_grid_probe.json")
def download(info,dest):
 url="https://china.scidb.cn/download?fileId="+info["id"]
 req=urllib.request.Request(url,headers={"User-Agent":"RetirementClimateResearch/1.0"})
 h=hashlib.sha256(); n=0
 with urllib.request.urlopen(req,timeout=180) as r:
  status=r.status; final=r.geturl(); ctype=r.headers.get("Content-Type")
  with dest.open("wb") as f:
   while True:
    b=r.read(4*1024*1024)
    if not b: break
    f.write(b);h.update(b);n+=len(b)
 return {"http_status":status,"final_url":final,"content_type":ctype,"bytes":n,"sha256":h.hexdigest()}
def main():
 import rasterio, numpy as np
 result={"schema":"RET_SCIDB_NATIONAL_1KM_CLIMATE_DOWNLOAD_QA_V1","dataset_id":DATASET_ID,
  "tested_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"formal_valid_county_screenings":0,
  "county_exclusions":0,"files":{},"notes":["tasmax is monthly mean of daily maximum temperature, not monthly all-time maximum.",
  "sunp is percentage of sunshine duration, not sunshine hours; do not compare directly with 1800h until converted/validated."]}
 BASE.mkdir(parents=True,exist_ok=True)
 for key,info in FILES.items():
  dest=BASE/info["name"]
  try:
   if not dest.exists() or dest.stat().st_size!=info["expected"]:
    qa=download(info,dest)
   else:
    raw=dest.read_bytes();qa={"http_status":200,"bytes":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"reused_existing":True}
   if qa["bytes"]!=info["expected"]: raise RuntimeError("SIZE_MISMATCH expected=%s got=%s"%(info["expected"],qa["bytes"]))
   with zipfile.ZipFile(dest) as z:
    members=[m for m in z.infolist() if m.filename.lower().endswith((".tif",".tiff"))]
    if not members: raise RuntimeError("NO_GEOTIFF_IN_ARCHIVE")
    member=members[0]
    with z.open(member) as src:
     tif=BASE/(key+".tif")
     with tif.open("wb") as f:
      while True:
       b=src.read(8*1024*1024)
       if not b: break
       f.write(b)
   with rasterio.open(tif) as ds:
    sample=[]
    for b in range(1,ds.count+1):
     a=ds.read(b,out_shape=(min(1000,ds.height),min(1000,ds.width)),masked=True)
     vals=a.compressed(); vals=vals[np.isfinite(vals) & (vals > -1e20)]
     sample.append({"band":b,"sample_valid":int(vals.size),"sample_min":float(vals.min()) if vals.size else None,
       "sample_max":float(vals.max()) if vals.size else None,"sample_mean":float(vals.mean()) if vals.size else None})
    qa.update({"archive_sha256":qa["sha256"],"geotiff_member":member.filename,"geotiff_bytes":tif.stat().st_size,
      "geotiff_sha256":hashlib.sha256(tif.read_bytes()).hexdigest(),"crs":str(ds.crs),"width":ds.width,
      "height":ds.height,"bands":ds.count,"dtype":ds.dtypes[0],"nodata":ds.nodata,
      "bounds":list(ds.bounds),"transform":list(ds.transform),"band_samples":sample})
   result["files"][key]=qa
  except Exception as e:
   result["files"][key]={"status":"FAILED","error_type":type(e).__name__,"error":str(e)[:1500]}
 result["status"]="DOWNLOAD_AND_RASTER_QA_PASS" if all(x.get("http_status")==200 and x.get("geotiff_bytes",0)>0 for x in result["files"].values()) else "DOWNLOAD_OR_RASTER_QA_BLOCKED"
 OUT.parent.mkdir(parents=True,exist_ok=True);OUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(result,ensure_ascii=False)[:20000])
 if result["status"]!="DOWNLOAD_AND_RASTER_QA_PASS":sys.exit(2)
if __name__=="__main__":main()
