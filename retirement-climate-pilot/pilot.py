#!/usr/bin/env python3
"""Exploratory engineering smoke test only. ERA5 reanalysis is NOT CMA normals.
No county suitability decisions are made by this script.
"""
import csv, json, os, pathlib, statistics, time, urllib.error, urllib.parse, urllib.request
from datetime import datetime
OUT=pathlib.Path("retirement-climate-pilot/output")
OUT.mkdir(parents=True,exist_ok=True)
SITES=[("Haikou",20.04,110.35),("Kunming",25.04,102.71),("Xiamen",24.48,118.09),("Panzhihua",26.58,101.72),("Mengzi",23.37,103.39),("Jinghong",22.01,100.80),("Guilin",25.27,110.29),("Quanzhou",24.87,118.68),("Dali",25.61,100.27),("Guiyang",26.65,106.63),("Nanning",22.82,108.37),("Sanya",18.25,109.51)]
BASE="https://archive-api.open-meteo.com/v1/archive"
results=[]
for name,lat,lon in SITES:
    params={"latitude":lat,"longitude":lon,"start_date":"1991-01-01","end_date":"2020-12-31",
      "daily":"temperature_2m_mean,temperature_2m_max,temperature_2m_min,precipitation_sum,sunshine_duration",
      "timezone":"Asia/Shanghai","models":"era5"}
    url=BASE+"?"+urllib.parse.urlencode(params)
    req=urllib.request.Request(url,headers={"User-Agent":"retirement-climate-pilot/0.1"})
    try:
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req,timeout=90) as response:
                    payload=response.read()
                break
            except urllib.error.HTTPError as err:
                if err.code not in (429,500,502,503,504) or attempt == 3:
                    raise
                time.sleep(12 * (attempt + 1))
        time.sleep(3)
        data=json.loads(payload)
        (OUT/(name+".json")).write_bytes(payload)
        daily=data["daily"]
        days=len(daily["time"])
        if days < 10000: raise ValueError("insufficient daily rows: "+str(days))
        for month in range(1,13):
            idx=[i for i,date in enumerate(daily["time"]) if int(date[5:7])==month]
            def avg(field):
                v=[daily[field][i] for i in idx if daily[field][i] is not None]
                return round(statistics.mean(v),2) if v else None
            results.append({"site":name,"latitude":lat,"longitude":lon,"month":month,
              "days":len(idx),"mean_temp_c":avg("temperature_2m_mean"),
              "mean_daily_max_c":avg("temperature_2m_max"),"mean_daily_min_c":avg("temperature_2m_min"),
              "mean_daily_precip_mm":avg("precipitation_sum"),
              "mean_daily_sunshine_seconds":avg("sunshine_duration"),
              "source_url":url,"source":"Open-Meteo ERA5 reanalysis; NOT CMA station normals",
              "period":"1991-2020","status":"EXPLORATORY_ONLY"})
    except Exception as exc:
        results.append({"site":name,"status":"FETCH_OR_PARSE_FAILED","error":repr(exc),"source_url":url})
fields=["site","latitude","longitude","month","days","mean_temp_c","mean_daily_max_c",
"mean_daily_min_c","mean_daily_precip_mm","mean_daily_sunshine_seconds","source_url",
"source","period","status","error"]
with (OUT/"monthly_pilot.csv").open("w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(results)
summary={"generated_utc":datetime.utcnow().isoformat()+"Z","sites_requested":len(SITES),
"sites_with_12_months":len({r["site"] for r in results if r["status"]=="EXPLORATORY_ONLY"}),
"monthly_rows":sum(r["status"]=="EXPLORATORY_ONLY" for r in results),
"raw_daily_rows":sum(r.get("days",0) for r in results if r["status"]=="EXPLORATORY_ONLY"),
"county_matched":0,"valid_county_screenings":0,
"caveat":"ERA5 point reanalysis is exploratory; no administrative joins, no formal classifications.",
"errors":[{"site":r["site"],"error":r.get("error")} for r in results if r["status"]!="EXPLORATORY_ONLY"]}
(OUT/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(summary,ensure_ascii=False))
if summary["sites_with_12_months"]==0: raise SystemExit(2)
