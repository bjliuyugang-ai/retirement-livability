#!/usr/bin/env python3
"""Point-level sensitivity diagnostics, NOT county screening or formal grades."""
import csv,json,pathlib
from collections import defaultdict
p=pathlib.Path("retirement-climate-pilot/output")
rows=list(csv.DictReader((p/"monthly_pilot.csv").open(encoding="utf-8-sig")))
ext={r["site"]:r for r in csv.DictReader((p/"daily_extremes_pilot.csv").open(encoding="utf-8-sig"))}
by=defaultdict(dict)
for r in rows:
    if r["status"]=="EXPLORATORY_ONLY":
        by[r["site"]][int(r["month"])]=r
out=[]
for site,months in sorted(by.items()):
    if len(months)!=12 or site not in ext: continue
    def mean(keys,col):
        return round(sum(float(months[m][col]) for m in keys)/len(keys),2)
    winter=mean([12,1,2],"mean_temp_c")
    summer=mean([6,7,8],"mean_daily_max_c")
    winter_sun=mean([12,1,2],"mean_daily_sunshine_seconds")/3600
    hot=float(ext[site]["hot_days_ge35_annual_mean"])
    scenarios=[
      {"name":"broad","winter_min":8,"summer_max":33,"winter_sun_min":2,"hot_days_max":90},
      {"name":"middle","winter_min":11,"summer_max":31,"winter_sun_min":3,"hot_days_max":45},
      {"name":"selective","winter_min":14,"summer_max":29,"winter_sun_min":4,"hot_days_max":20}]
    assessments=[]
    for s in scenarios:
        failed=[k for k,test in [
          ("winter_temp",winter<s["winter_min"]),
          ("summer_daily_max",summer>s["summer_max"]),
          ("winter_sun",winter_sun<s["winter_sun_min"]),
          ("hot_days",hot>s["hot_days_max"])] if test]
        assessments.append({"scenario":s["name"],"flags":failed,"passes_exploratory":not failed})
    out.append({"site":site,"winter_mean_c":winter,"summer_mean_daily_max_c":summer,
      "winter_sun_hours_per_day":round(winter_sun,2),"hot_days_ge35_per_year":hot,
      "scenarios":assessments,"classification":"UNASSESSED_COUNTY",
      "limitations":"Point ERA5; thresholds hypothetical; no county polygons, elevation exceptions, air/water/risk checks."})
(p/"point_sensitivity.json").write_text(json.dumps({"site_count":len(out),"results":out},ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps({"sensitivity_sites":len(out),"scenarios":3,"county_screenings":0},ensure_ascii=False))
