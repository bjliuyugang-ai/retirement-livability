#!/usr/bin/env python3
"""RET-CLIMATE-SPATIAL-REPRESENTATIVENESS-002, multi-grid ERA5 comparison.

Frozen scope: 4 terrain-heterogeneous historical counties, three preexisting
coordinates each, 1991-2020 ERA5. Operational repair: group requests by county
(4 multi-location calls instead of 12 single-point calls). No formal county
screenings; current official identities, terrain exceptions and station checks
remain open. Actual ERA5 grid centers are audited separately from requested
coordinates so repeated grid cells cannot masquerade as independent evidence.
"""
import datetime,gzip,hashlib,json,pathlib,statistics,time,urllib.error,urllib.parse,urllib.request
ROOT=pathlib.Path("research_engine/retirement")
PREV=ROOT/"status/latest-microclimate-pilot.json"
OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
CASES=["Panzhihua","Mengzi","Jinghong","Dali"]
VARIABLES="temperature_2m_mean,temperature_2m_max,temperature_2m_min,sunshine_duration,relative_humidity_2m_mean,dew_point_2m_mean"
res={"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "status":"RUNNING","action_id":"RET-CLIMATE-SPATIAL-REPRESENTATIVENESS-002",
 "source":"Open-Meteo archive, ERA5 1991-2020; NOT CMA station normals",
 "method_version":"COUNTY_3_POINT_MULTI_LOCATION_BATCH_V2",
 "official_2026_roster_verified":False,"formal_county_screenings":0,
 "note":"Historic nonofficial county polygons, DEM-based 3-point sampling and coarse ERA5 reanalysis. Grid duplicates and terrain exceptions remain explicitly unresolved. No grades or exclusions.",
 "case_count_requested":4,"point_requests_expected":12,"cases":[],"errors":[]}
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"retirement-climate-spatial-qa/0.2"})
    for retry in range(4):
        try:
            with urllib.request.urlopen(req,timeout=150) as r:return r.read()
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as ex:
            if isinstance(ex,urllib.error.HTTPError) and ex.code not in (429,500,502,503,504):raise
            if retry==3:raise
            time.sleep(10*(retry+1))
def point_metrics(payload,request_point,raw_sha,source_url,index):
    d=payload["daily"];dates=d["time"]
    if len(dates)!=10958:raise ValueError("Unexpected 1991-2020 daily coverage: "+str(len(dates)))
    m={}
    for key in VARIABLES.split(","):
        vals=d[key]
        if len(vals)!=len(dates):raise ValueError("Length mismatch: "+key)
        for label,months in [("annual",range(1,13)),("winter",[12,1,2]),("summer",[6,7,8])]:
            matched=[v for v,date in zip(vals,dates) if int(date[5:7]) in months]
            valid=[float(v) for v in matched if v is not None]
            if len(valid)<.99*len(matched):raise ValueError("Too many missing daily values: "+key)
            m[label+"_"+key]=round(statistics.mean(valid),3)
    return {"requested_latitude":request_point["latitude"],"requested_longitude":request_point["longitude"],
      "latitude":request_point["latitude"],"longitude":request_point["longitude"],
      "elevation_m":request_point["copernicus_glo90_elevation_m"],"raw_sha256":raw_sha,
      "source_response_index":index,"daily_rows":len(dates),"source_url":source_url,"metrics":m,
      "era5_grid_center_latitude":payload.get("latitude"),
      "era5_grid_center_longitude":payload.get("longitude"),
      "era5_grid_elevation_m":payload.get("elevation")}
try:
    prev=json.loads(PREV.read_text(encoding="utf-8"))
    if prev.get("status")!="PASS_ELEVATION_SENSITIVITY":raise RuntimeError("Previous DEM point positions lack accepted evidence")
    sites={x["site"]:x for x in prev["points"]}
    for case in CASES:
        source=sites[case]
        req_points=source["points"]
        if len(req_points)!=3:raise RuntimeError("Frozen county sample size is not 3: "+case)
        params={"latitude":",".join(str(p["latitude"]) for p in req_points),
                "longitude":",".join(str(p["longitude"]) for p in req_points),
                "start_date":"1991-01-01","end_date":"2020-12-31",
                "daily":VARIABLES,"timezone":"Asia/Shanghai","models":"era5"}
        url="https://archive-api.open-meteo.com/v1/archive?"+urllib.parse.urlencode(params,safe=",")
        record={"site":case,"archival_county_candidate":source["candidate_county_code"],
           "dem_span_m":source["sample_dem_span_m"],"requested":3,
           "succeeded":0,"samples":[],"metric_spans":{},
           "county_representativeness_confirmed":False,"microclimate_exception_not_closed":True}
        try:
            raw=get(url)
            raw_sha=hashlib.sha256(raw).hexdigest()
            (OUT/("raw_era5_multi_"+case+".json.gz")).write_bytes(gzip.compress(raw))
            payload=json.loads(raw)
            if not isinstance(payload,list) or len(payload)!=3:
                raise ValueError("Expected ordered JSON list of 3 Open-Meteo locations")
            record["batch_response_sha256"]=raw_sha
            record["batch_source_url"]=url
            points=[]
            for i,(item,rpoint) in enumerate(zip(payload,req_points)):
                try:points.append(point_metrics(item,rpoint,raw_sha,url,i))
                except Exception as exc:
                    points.append({"latitude":rpoint["latitude"],"longitude":rpoint["longitude"],
                                   "error":repr(exc),"source_response_index":i})
                    res["errors"].append({"site":case,"index":i,"error":repr(exc)})
            record["samples"]=points
            valid=[p for p in points if "metrics" in p]
            record["succeeded"]=len(valid)
            if len(valid)==3:
                for metric in ["winter_temperature_2m_mean","summer_temperature_2m_max",
                               "winter_sunshine_duration","summer_dew_point_2m_mean",
                               "summer_relative_humidity_2m_mean"]:
                    values=[x["metrics"][metric] for x in valid]
                    record["metric_spans"][metric]={"min":min(values),"max":max(values),
                                                      "span":round(max(values)-min(values),3)}
                centers={(p["era5_grid_center_latitude"],p["era5_grid_center_longitude"]) for p in valid}
                record["unique_era5_grid_centers"]=len(centers)
                record["grid_resolution_qa"]=("INSUFFICIENT_INDEPENDENT_GRIDS" if len(centers)<2
                    else "MULTIPLE_GRID_CENTERS_BUT_NOT_FULL_COUNTY_REPRESENTATIVENESS")
            print("COUNTY_BATCH",case,"successful_points",record["succeeded"],
                  "unique_grids",record.get("unique_era5_grid_centers"),flush=True)
        except Exception as exc:
            record["error"]=repr(exc)
            res["errors"].append({"site":case,"error":repr(exc)})
            print("COUNTY_BATCH_BLOCKED",case,repr(exc),flush=True)
        res["cases"].append(record)
        time.sleep(4)
    res["request_count_completed"]=sum(x["succeeded"] for x in res["cases"])
    res["all_four_terrain_cases_complete"]=all(x["succeeded"]==3 for x in res["cases"])
    res["four_counties_with_multiple_grid_centers"]=sum(x.get("unique_era5_grid_centers",0)>=2 for x in res["cases"])
    res["status"]=("PASS_EXPLORATORY_SPATIAL_VARIABILITY" if res["all_four_terrain_cases_complete"]
                   else "PARTIAL_BLOCKED_WITH_EVIDENCE")
except Exception as exc:res.update({"status":"BLOCKED_WITH_EVIDENCE","error":repr(exc)})
(OUT/"spatial_variability_002.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:v for k,v in res.items() if k!="cases"},ensure_ascii=False),flush=True)
if res["status"]!="PASS_EXPLORATORY_SPATIAL_VARIABILITY":raise SystemExit(2)
