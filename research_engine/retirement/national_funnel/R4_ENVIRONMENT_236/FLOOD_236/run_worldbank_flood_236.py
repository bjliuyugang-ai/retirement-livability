#!/usr/bin/env python3
"""R4 nationwide 236-candidate 100-year river-flood hazard overlay.

Source: World Bank GAR flood extent (1km). Modelled fluvial flooding, not an
observed event; no pluvial/coastal flooding, defenses or dwelling addresses.
Output is only a risk-screening signal. Never hard-exclude from this layer.
"""
from __future__ import annotations
import csv, hashlib, json, math, os, pathlib, urllib.request, time, traceback
import numpy as np, rasterio
from rasterio.features import geometry_mask
from rasterio.windows import from_bounds, transform as window_transform, Window
from rasterio.warp import transform_geom, reproject, Resampling
from shapely.geometry import shape, mapping
from datetime import datetime, timezone

ROOT=pathlib.Path("research_engine/retirement")
BASE=ROOT/"national_funnel/R4_ENVIRONMENT_236/FLOOD_236"
CAND=ROOT/"national_funnel/FINAL_FILTER/runs/42453646573/FINAL_CARRY_FORWARD_AFTER_R1_R2_R3.csv"
OUT=BASE/"output";CACHE=BASE/"cache"
SOURCE_URL="https://datacatalogfiles.worldbank.org/ddh-published/0067118/DR0096180/fl_hazard_100_yrp.tif"
SOURCE_META="https://datacatalog.worldbank.org/search/dataset/0067118/flood-hazard-100-year-return-period"
GEO_URL="https://raw.githubusercontent.com/zzhonglei/GeoCode-Release/main/contributions/china-admin-boundaries/skill/data/china_county.geojson"
GEO_SHA="22db6c54b9cb0118ecdcc8a117bf2da4fc24a2229cdba7e6e55dbb5dd56e8246"
POP_FILENAME="global_pop_2024_UC_1km_R2024B_v1.tif"
POP_PATH=ROOT/"national_funnel/R1/cache"/POP_FILENAME
POP_URL="https://data.worldpop.org/GIS/Population/Global_2015_2030/R2024B/2024/0_Mosaicked/v1/1km/unconstrained/"+POP_FILENAME

def utc():return datetime.now(timezone.utc).isoformat()
def download(url,dest):
 dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists() and dest.stat().st_size>4_000_000:return {"status":"REUSED","bytes":dest.stat().st_size}
 p=dest.with_suffix(dest.suffix+".part");p.unlink(missing_ok=True)
 last=None
 for attempt in range(1,4):
  try:
   req=urllib.request.Request(url,headers={"User-Agent":"R4National236FloodScreen/1.0","Accept":"*/*"})
   with urllib.request.urlopen(req,timeout=90) as response, p.open("wb") as out:
    while True:
     b=response.read(4*1024*1024)
     if not b:break
     out.write(b)
   if p.stat().st_size<4_000_000:raise RuntimeError("Unexpectedly short TIF "+str(p.stat().st_size))
   p.replace(dest)
   return {"status":"DOWNLOADED","bytes":dest.stat().st_size,"attempt":attempt}
  except Exception as e:
   last=repr(e);p.unlink(missing_ok=True);time.sleep(2*attempt)
 raise RuntimeError("SOURCE_DOWNLOAD_FAILED "+str(last))
def candidates():
 with CAND.open(encoding="utf-8-sig",newline="") as f:rows=list(csv.DictReader(f))
 if len(rows)!=236 or len(set(x["code"] for x in rows))!=236:raise RuntimeError("CANDIDATES_CHANGED")
 return rows
def geoms():
 req=urllib.request.Request(GEO_URL,headers={"User-Agent":"R4National236FloodScreen/1.0"})
 with urllib.request.urlopen(req,timeout=90) as r: b=r.read()
 sha=hashlib.sha256(b).hexdigest()
 if sha!=GEO_SHA:raise RuntimeError("GEO_SHA_MISMATCH:"+sha)
 areas={}
 for f in json.loads(b.decode("utf-8")).get("features",[]):
  p=f.get("properties") or {};code=str(p.get("adcode") or "")
  if len(code)==6 and f.get("geometry"):areas[code]={"name":p.get("name"),"geom":f["geometry"]}
 return areas
def save(rows,summary):
 OUT.mkdir(parents=True,exist_ok=True)
 if rows:
  with (OUT/"NATIONAL_236_FLOOD_RP100_CANDIDATE_SCREEN.csv").open("w",encoding="utf-8-sig",newline="") as f:
   w=csv.DictWriter(f,fieldnames=list(rows[0]),extrasaction="ignore");w.writeheader();w.writerows(rows)
 (OUT/"NATIONAL_236_FLOOD_RP100_SUMMARY.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
def main():
 OUT.mkdir(parents=True,exist_ok=True)
 rows=candidates()
 areas=geoms()
 flood_path=CACHE/"fl_hazard_100_yrp.tif"
 failures=[]
 try:info=download(SOURCE_URL,flood_path)
 except Exception as e:failures.append(repr(e));info={"status":"PENDING_DOWNLOAD","error":repr(e)}
 basefields={"flood_area_cell_count":None,"flood_positive_cell_count":None,
  "flood_positive_area_grid_share":None,"flood_population_share_2024_proxy":None,
  "flood_population_weight_sum_2024_proxy":None}
 candidate_results=[];metadata=None
 if info["status"]!="PENDING_DOWNLOAD":
  try:
   with rasterio.open(flood_path) as src:
    dec=src.read(1,out_shape=(1,min(src.height,280),min(src.width,560)),masked=True,resampling=Resampling.nearest)
    sample=np.asarray(dec.filled(-99999)).ravel()
    vals,counts=np.unique(sample,return_counts=True)
    sampled=sorted(zip(vals.tolist(),counts.tolist()),key=lambda x:-x[1])[:25]
    metadata={"driver":src.driver,"shape":[src.height,src.width],"dtype":src.dtypes[0],
      "crs":str(src.crs),"nodata":src.nodata,"bounds":list(src.bounds),
      "pixel_size":[src.res[0],src.res[1]],
      "band_description":src.descriptions[0],"tags":src.tags(),"sample_value_counts":sampled}
    values=set(int(v) for v in vals if np.isfinite(v) and v!=-99999)
    # Binary 0 dry / 1 flood expected. If not, avoid making a spurious risk map.
    semantics_ok=values.issubset({0,1}) and 1 in values
    metadata["binary_extent_semantics_provisionally_valid"]=semantics_ok
    if not semantics_ok:failures.append("FLOOD_PIXEL_VALUES_NOT_VALIDATED_BINARY:"+repr(sorted(values)[:30]))
    popsrc=rasterio.open(POP_PATH) if POP_PATH.exists() else None
    for c in rows:
     code=c["code"];g=areas.get(code)
     item={"code":code,"name":c["name"],
       "R1_status":c["R1_next_round_status"],"winter_status":c["winter_status"],"summer_status":c["summer_status"],
       "geometry_status":"MATCH" if g and g["name"]==c["name"] else "PENDING_GEOMETRY",
       "flood_rp100_screen_status":"PENDING",
       **basefields,"hard_R4_exclusion":"NO","grade_change":"NO",
       "interpretation":"GAR 1km 100-year modelled riverine flood hazard; not house-level and not hard-exclusion evidence"}
     if not g or g["name"]!=c["name"]:
      item["flood_rp100_screen_status"]="PENDING_GEOMETRY";candidate_results.append(item);continue
     if not semantics_ok:
      item["flood_rp100_screen_status"]="PENDING_PIXEL_SEMANTICS";candidate_results.append(item);continue
     try:
      geom=g["geom"]
      if src.crs and str(src.crs)!="EPSG:4326":geom=transform_geom("EPSG:4326",src.crs,geom)
      b=shape(geom).bounds
      win=from_bounds(*b,transform=src.transform).round_offsets().round_lengths()
      x0=max(0,int(win.col_off));y0=max(0,int(win.row_off))
      x1=min(src.width,int(win.col_off+win.width));y1=min(src.height,int(win.row_off+win.height))
      if x1<=x0 or y1<=y0:
       item["flood_rp100_screen_status"]="PENDING_NO_RASTER_OVERLAP";candidate_results.append(item);continue
      w=Window(x0,y0,x1-x0,y1-y0)
      a=src.read(1,window=w,masked=True)
      tr=window_transform(w,src.transform)
      inside=geometry_mask([geom],out_shape=a.shape,transform=tr,invert=True,all_touched=False)
      mask=inside & np.isfinite(np.asarray(a.filled(np.nan)))
      all_count=int(np.count_nonzero(inside))
      hazard=(np.asarray(a.filled(0))>0) & inside
      flooded=int(np.count_nonzero(hazard))
      item["flood_area_cell_count"]=all_count
      item["flood_positive_cell_count"]=flooded
      item["flood_positive_area_grid_share"]=flooded/all_count if all_count else None
      if popsrc is not None:
       weights=np.zeros(a.shape,dtype="float32")
       reproject(source=rasterio.band(popsrc,1),destination=weights,
        src_transform=popsrc.transform,src_crs=popsrc.crs,src_nodata=popsrc.nodata,
        dst_transform=tr,dst_crs=src.crs,dst_nodata=0,resampling=Resampling.average)
       weights[~np.isfinite(weights)]=0;weights[weights<0]=0
       inhabited=inside & (weights>0)
       total=float(np.sum(weights[inhabited]))
       item["flood_population_weight_sum_2024_proxy"]=total if total>0 else None
       item["flood_population_share_2024_proxy"]=float(np.sum(weights[hazard & inhabited])/total) if total>0 else None
      item["flood_rp100_screen_status"]="MODEL_SCREENED_WITH_POPULATION_PROXY" if item["flood_population_share_2024_proxy"] is not None else "MODEL_SCREENED_AREA_ONLY_POPULATION_PENDING"
     except Exception as e:
      item["flood_rp100_screen_status"]="PENDING_REGION_ERROR"
      failures.append(code+":"+repr(e))
     candidate_results.append(item)
     if len(candidate_results)%25==0:print("FLOOD_PROGRESS",len(candidate_results),flush=True)
    if popsrc is not None:popsrc.close()
  except Exception as e:failures.append("OPEN_OR_READ_FAILED "+repr(e))
 if len(candidate_results)!=236:
  indexed={x["code"]:x for x in candidate_results}
  for c in rows:
   if c["code"] not in indexed:
    indexed[c["code"]]={"code":c["code"],"name":c["name"],
     "R1_status":c["R1_next_round_status"],"winter_status":c["winter_status"],"summer_status":c["summer_status"],
     "geometry_status":"NOT_COMPUTED","flood_rp100_screen_status":"PENDING_SOURCE_ERROR",**basefields,
     "hard_R4_exclusion":"NO","grade_change":"NO","interpretation":"Missing or unavailable source cannot establish safety or failure"}
  candidate_results=[indexed[c["code"]] for c in rows]
 status_count={k:sum(x["flood_rp100_screen_status"]==k for x in candidate_results) for k in sorted(set(x["flood_rp100_screen_status"] for x in candidate_results))}
 ranked=sorted([x for x in candidate_results if x["flood_population_share_2024_proxy"] is not None],key=lambda x:x["flood_population_share_2024_proxy"],reverse=True)
 summary={"schema":"R4_NATIONAL_236_WORLDBANK_100YR_RIVER_FLOOD_FIRST_PASS_V1",
  "created_at_utc":utc(),"candidate_count":236,
  "source_url":SOURCE_URL,"source_metadata":SOURCE_META,"source_file":info,
  "raster_metadata":metadata,"population_source":str(POP_PATH) if POP_PATH.exists() else "PENDING_WORLDPOP_CACHE",
  "source_limitations":["World Bank GAR Atlas static 1km riverine flood extent; model may overestimate small return periods and does not consider flood defenses.",
    "Does not include local pluvial/flash flood, urban drainage, coast/sea level, or high-resolution levee performance.",
    "County-wide grid ratio is not a residential address exposure estimate; WorldPop population map is an estimated spatial proxy.",
    "A high grid fraction indicates verification priority only, and low fraction cannot establish a safe actual home site."],
  "status_counts":status_count,
  "ranking_top_modelled_population_share":[{"code":x["code"],"name":x["name"],"population_weighted_share":x["flood_population_share_2024_proxy"]} for x in ranked[:25]],
  "failures":failures[:60],"formal_exclusions":0,"grade_changes":0,
  "candidate_count_remaining":236,"prior_58_pending_also_included":True}
 save(candidate_results,summary)
 print("FLOOD_236_FINAL",json.dumps({"count":236,"statuses":status_count,"top":summary["ranking_top_modelled_population_share"][:5],
  "error_count":len(failures),"formal_exclusions":0},ensure_ascii=False),flush=True)
if __name__=="__main__":main()
