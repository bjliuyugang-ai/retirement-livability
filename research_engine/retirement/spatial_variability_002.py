#!/usr/bin/env python3
"""Frozen 4-case terrain counterexample assay. ERA5 1991-2020, 3 grid-point requests/site.
Exploratory only; no 2026 boundary validity, no CMA normals, no formal county grades.
"""
import datetime,hashlib,json,pathlib,statistics,time,urllib.parse,urllib.request,urllib.error
ROOT=pathlib.Path("research_engine/retirement")
PREV=ROOT/"status/latest-microclimate-pilot.json"
OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
CASES=["Panzhihua","Mengzi","Jinghong","Dali"]
res={"generated_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"status":"RUNNING","action_id":"RET-CLIMATE-SPATIAL-REPRESENTATIVENESS-002",
"source":"Open-Meteo archive ERA5 1991-2020; NOT CMA official normals",
"official_2026_roster_verified":False,"formal_county_screenings":0,
"note":"Three samples per historic nonofficial county polygon. ERA5 coarser than DEM; only climate heterogeneity counterexamples, not official ratings.",
"case_count_requested":4,"point_requests_expected":12,"cases":[],"errors":[]}
def get(url):
    req=urllib.request.Request(url,headers={"User-Agent":"retirement-climate-spatial-qa/0.2"})
    for retry in range(4):
        try:
            with urllib.request.urlopen(req,timeout=110) as r:return r.read()
        except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError) as ex:
            if isinstance(ex,urllib.error.HTTPError) and ex.code not in (429,500,502,503,504):raise
            if retry==3:raise
            time.sleep(10*(retry+1))
def compute(p):
    args={"latitude":p["latitude"],"longitude":p["longitude"],
      "start_date":"1991-01-01","end_date":"2020-12-31",
      "daily":"temperature_2m_mean,temperature_2m_max,temperature_2m_min,sunshine_duration,relative_humidity_2m_mean,dew_point_2m_mean",
      "timezone":"Asia/Shanghai","models":"era5"}
    url="https://archive-api.open-meteo.com/v1/archive?"+urllib.parse.urlencode(args)
    b=get(url);payload=json.loads(b);d=payload["daily"];dates=d["time"]
    if len(dates)!=10958:raise ValueError("Unexpected daily coverage "+str(len(dates)))
    m={}
    for key in args["daily"].split(","):
        vals=d[key]
        if len(vals)!=len(dates):raise ValueError("Shape mismatch "+key)
        def mean_for(months):
            sel=[float(v) for v,date in zip(vals,dates) if v is not None and int(date[5:7]) in months]
            if len(sel)<.99*sum(int(x[5:7]) in months for x in dates):raise ValueError("Missing >1% "+key)
            return round(statistics.mean(sel),3)
        m["annual_"+key]=mean_for(range(1,13))
        m["winter_"+key]=mean_for([12,1,2])
        m["summer_"+key]=mean_for([6,7,8])
    return {"latitude":p["latitude"],"longitude":p["longitude"],"elevation_m":p["copernicus_glo90_elevation_m"],
      "raw_sha256":hashlib.sha256(b).hexdigest(),"daily_rows":len(dates),"source_url":url,"metrics":m,
      "era5_grid_center_latitude":payload.get("latitude"),"era5_grid_center_longitude":payload.get("longitude"),
      "era5_grid_elevation_m":payload.get("elevation"),"grid_resolution_warning":"ERA5 points may resolve to the same model grid"}
try:
    old=json.loads(PREV.read_text(encoding="utf-8"))
    arr={x["site"]:x for x in old["points"]}
    for case in CASES:
        source=arr[case]
        points=[]
        for p in source["points"]:
            try:points.append(compute(p))
            except Exception as exc:
                points.append({"latitude":p["latitude"],"longitude":p["longitude"],"error":repr(exc)})
                res["errors"].append({"case":case,"coordinate":[p["latitude"],p["longitude"]],"error":repr(exc)})
            time.sleep(3)
        success=[x for x in points if "metrics" in x]
        spread={}
        if len(success)==3:
            for key in ["winter_temperature_2m_mean","summer_temperature_2m_max","winter_sunshine_duration",
                        "summer_dew_point_2m_mean","summer_relative_humidity_2m_mean"]:
                values=[p["metrics"][key] for p in success]
                spread[key]={"min":min(values),"max":max(values),"span":round(max(values)-min(values),3)}
        grid_centers={(p.get("era5_grid_center_latitude"),p.get("era5_grid_center_longitude")) for p in success}
        res["cases"].append({"site":case,"archival_county_candidate":source["candidate_county_code"],
           "dem_span_m":source["sample_dem_span_m"],"requested":3,
           "succeeded":len(success),"samples":points,"metric_spans":spread,
           "unique_era5_grid_centers":len(grid_centers),
           "grid_resolution_qa":"INSUFFICIENT_RESOLUTION" if len(grid_centers)<2 else "MULTIPLE_GRIDS_NOT_FULL_COVERAGE",
           "county_representativeness_confirmed":False,"microclimate_exception_not_closed":True})
    res["request_count_completed"]=sum(x["succeeded"] for x in res["cases"])
    res["all_four_terrain_cases_complete"]=all(x["succeeded"]==3 for x in res["cases"])
    res["four_counties_with_multiple_grid_centers"]=sum(x["unique_era5_grid_centers"]>=2 for x in res["cases"])
    res["status"]="PASS_EXPLORATORY_SPATIAL_VARIABILITY" if res["all_four_terrain_cases_complete"] else "PARTIAL_BLOCKED_WITH_EVIDENCE"
except Exception as exc:res.update({"status":"BLOCKED_WITH_EVIDENCE","error":repr(exc)})
(OUT/"spatial_variability_002.json").write_text(json.dumps(res,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:v for k,v in res.items() if k!="cases"},ensure_ascii=False))
if res["status"]!="PASS_EXPLORATORY_SPATIAL_VARIABILITY":raise SystemExit(2)
