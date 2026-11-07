#!/usr/bin/env python3
"""Bounded single-point recovery for RET-CLIMATE-SPATIAL-REPRESENTATIVENESS-002.

Reuses independently frozen 11/12 ERA5 exploratory metrics; never re-downloads
successful points. Makes at most two attempts for the one incomplete Dali
coordinate. Does not assert distinct ERA5 grid cells where raw location
metadata from earlier requests is unavailable. No official county screenings.
"""
import copy,datetime,gzip,hashlib,json,pathlib,statistics,time,urllib.error,urllib.parse,urllib.request
ROOT=pathlib.Path("research_engine/retirement")
CACHE=ROOT/"evidence/spatial_002_frozen_partial_42315459712.json"
OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
VARS="temperature_2m_mean,temperature_2m_max,temperature_2m_min,sunshine_duration,relative_humidity_2m_mean,dew_point_2m_mean"
METRICS=["winter_temperature_2m_mean","summer_temperature_2m_max","winter_sunshine_duration",
         "summer_dew_point_2m_mean","summer_relative_humidity_2m_mean"]
def one_point(point):
    args={"latitude":point["latitude"],"longitude":point["longitude"],
          "start_date":"1991-01-01","end_date":"2020-12-31","daily":VARS,
          "timezone":"Asia/Shanghai","models":"era5"}
    url="https://archive-api.open-meteo.com/v1/archive?"+urllib.parse.urlencode(args)
    req=urllib.request.Request(url,headers={"User-Agent":"retirement-single-point-recovery/1.0"})
    raw=None
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req,timeout=42) as r:raw=r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code!=429 or attempt==1:raise
            print("RATE_LIMIT_429","attempt",attempt+1,"retry_after_bounded",flush=True)
            time.sleep(12)
        except (urllib.error.URLError,TimeoutError):
            if attempt==1:raise
            time.sleep(5)
    if raw is None:raise RuntimeError("No ERA5 response")
    payload=json.loads(raw);daily=payload["daily"];dates=daily["time"]
    if len(dates)!=10958:raise ValueError("Incomplete 1991–2020 record: "+str(len(dates)))
    metrics={}
    for key in VARS.split(","):
        seq=daily[key]
        if len(seq)!=len(dates):raise ValueError("Wrong daily field length: "+key)
        for label,months in [("annual",range(1,13)),("winter",[12,1,2]),("summer",[6,7,8])]:
            selected=[v for dt,v in zip(dates,seq) if int(dt[5:7]) in months]
            valid=[float(v) for v in selected if v is not None]
            if len(valid)<0.99*len(selected):raise ValueError("Incomplete data: "+key+" "+label)
            metrics[label+"_"+key]=round(statistics.mean(valid),3)
    (OUT/"recovery_dali_missing_point_raw.json.gz").write_bytes(gzip.compress(raw))
    return {"latitude":point["latitude"],"longitude":point["longitude"],
      "elevation_m":None,"daily_rows":len(dates),"raw_sha256":hashlib.sha256(raw).hexdigest(),
      "source_url":url,"metrics":metrics,
      "era5_grid_center_latitude":payload.get("latitude"),
      "era5_grid_center_longitude":payload.get("longitude"),
      "reused_from_frozen_cache":False}
cache=json.loads(CACHE.read_text(encoding="utf-8"))
if (cache.get("request_count_completed")!=11
    or cache.get("formal_county_screenings")!=0
    or cache.get("frozen_evidence_context",{}).get("source_run_id")!="42315459712"):
    raise SystemExit("CACHE_PROVENANCE_INVALID")
data=copy.deepcopy(cache)
data.update({"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "status":"RUNNING","method_version":"SINGLE_MISSING_POINT_BOUNDED_RESUME",
             "recovery_cache_source_sha256":hashlib.sha256(CACHE.read_bytes()).hexdigest(),
             "recovery_requests_max":2,"formal_county_screenings":0,
             "official_2026_roster_verified":False,
             "note":"Eleven previously completed points are preserved; only failed coordinate retried. Previous original responses do not include grid-center identity, so independence is UNVERIFIED."})
data["errors"]=[]
missing=[]
for case in data["cases"]:
    for idx,p in enumerate(case.get("samples",[])):
        if "metrics" in p:
            p["reused_from_frozen_cache"]=True
            p["grid_identity_verified"]=False
        else:
            missing.append((case,idx,p))
if len(missing)!=1 or missing[0][0].get("site")!="Dali":raise SystemExit("EXPECTED_ONE_MISSING_DALI_POINT")
case,idx,p=missing[0]
try:
    recovered=one_point(p)
    recovered["elevation_m"]=3307.0 # frozen DEM anchor from prior recorded terrain evidence
    recovered["grid_identity_verified"]=bool(recovered.get("era5_grid_center_latitude") is not None)
    case["samples"][idx]=recovered
    case["succeeded"]=3
    case.pop("error",None)
    for metric in METRICS:
        values=[z["metrics"][metric] for z in case["samples"]]
        case["metric_spans"][metric]={"min":min(values),"max":max(values),"span":round(max(values)-min(values),3)}
except Exception as e:
    case["samples"][idx]["error"]=repr(e)
    data["errors"].append({"site":"Dali","coordinate":[p["latitude"],p["longitude"]],"error":repr(e)})
data["request_count_completed"]=sum(c["succeeded"] for c in data["cases"])
data["all_four_terrain_cases_complete"]=all(c["succeeded"]==3 for c in data["cases"])
data["cached_points_reused"]=11
data["new_points_retrieved"]=data["request_count_completed"]-11
data["distinct_grid_centers_verified_for_prior_cached_points"]=0
data["status"]=("PASS_EXPLORATORY_SPATIAL_VARIABILITY" if data["request_count_completed"]==12
                else "PARTIAL_BLOCKED_WITH_EVIDENCE")
(OUT/"spatial_variability_002.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({key:data[key] for key in ["status","request_count_completed","cached_points_reused","new_points_retrieved","errors"]},ensure_ascii=False),flush=True)
if data["status"]!="PASS_EXPLORATORY_SPATIAL_VARIABILITY":raise SystemExit(2)
