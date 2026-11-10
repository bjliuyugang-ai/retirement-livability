#!/usr/bin/env python3
"""One-shot island-climate adjudication: observed JMA 59981 monthly Tmax and NASA POWER daily Tmax average grids.
This does not infer sunshine duration from solar flux or hard-exclude from coarse grids.
"""
import requests,json,re,datetime,pathlib,csv,calendar,statistics,time,html
from bs4 import BeautifulSoup
root=pathlib.Path("research_engine/retirement/status");root.mkdir(parents=True,exist_ok=True)
sites=[("海南·西沙区","西沙永兴岛观象台59981",16.833,112.333),("海南·南沙区","永暑礁/永暑岛",9.621,112.974)]
rows=[]
for region,name,lat,lon in sites:
 rec={"region":region,"site":name,"lat":lat,"lon":lon,"monthlies":{},"period":"1991—2020"}
 api="https://power.larc.nasa.gov/api/temporal/monthly/point"
 params={"parameters":"T2M_MAX_AVG,T2M,T2M_MIN_AVG","community":"SB","longitude":lon,"latitude":lat,"start":1991,"end":2020,"format":"JSON"}
 try:
  r=requests.get(api,params=params,timeout=90);r.raise_for_status();data=r.json()
  p=data["properties"]["parameter"]
  out=[]
  for mm in range(1,13):
   vals=[p["T2M_MAX_AVG"].get(f"{yy}{mm:02d}") for yy in range(1991,2021)]
   vals=[float(v) for v in vals if isinstance(v,(int,float)) and -80<v<75]
   rec["monthlies"][f"{mm:02d}"]={"model_tmax_daily_mean_c":round(statistics.mean(vals),2) if len(vals)==30 else None,"valid_years":len(vals)}
  rec["model_hot_month_daily_tmax_mean_c"]=round(max(d["model_tmax_daily_mean_c"] for d in rec["monthlies"].values() if d["model_tmax_daily_mean_c"] is not None),2)
  rec["model_url"]=r.url
  rec["model_evidence_limit"]="NASA POWER MERRA-2 coarse grid (not official station normal); no hard elimination from model alone"
 except Exception as e:rec["model_error"]=str(e)
 rows.append(rec)
 print("NASA",region,rec.get("model_hot_month_daily_tmax_mean_c"),"error",rec.get("model_error"),flush=True)
# Climatview 59981 1991-2020 monthly Tmax; 30 windows to ensure full years.
base="https://ds.data.jma.go.jp/gmd/tcc/tcc/products/climate/climatview/graph_mkhtml.php"
jma_rows={}
jma_error=[]
for yy in range(1991,2021):
 try:
  pars={"e":0,"k":0,"m":6,"n":59981,"r":1,"s":3,"y":min(yy+2,2020)}
  r=requests.get(base,params=pars,timeout=25)
  r.raise_for_status()
  soup=BeautifulSoup(r.text,"html.parser")
  for tr in soup.find_all("tr"):
   tds=[x.get_text(" ",strip=True) for x in tr.find_all(["td","th"],recursive=False)]
   if not tds:continue
   dt=re.search(r"\b(19\d\d|20\d\d)-(0[1-9]|1[012])\b",tds[0])
   if not dt or len(tds)<3:continue
   year=int(dt.group(1));month=int(dt.group(2))
   if 1991<=year<=2020:
    try:
     tmax=float(tds[2])
     if -20<tmax<55:jma_rows[f"{year}-{month:02d}"]=tmax
    except:pass
  print("JMA page",yy,r.status_code,"found",len(jma_rows),"text",soup.get_text(" ",strip=True)[:50],flush=True)
 except Exception as e:jma_error.append(f"{yy}: {e}")
 time.sleep(.18)
mon={}
for m in range(1,13):
 vals=[jma_rows[f"{y}-{m:02d}"] for y in range(1991,2021) if f"{y}-{m:02d}" in jma_rows]
 mon[f"{m:02d}"]={"years":len(vals),"mean_of_observed_monthly_mean_daily_tmax_c":round(statistics.mean(vals),2) if len(vals)>=25 else None,"samples":vals}
station={"name":"XISHA DAO 59981","source":"Japan Meteorological Agency ClimatView observed monthly mean maximum temperature","url":base+"?e=0&k=0&m=6&n=59981&r=1&s=3&y=2020","valid_months":len(jma_rows),"monthlies":mon,"errors":jma_error}
ok=[x["mean_of_observed_monthly_mean_daily_tmax_c"] for x in mon.values() if x["mean_of_observed_monthly_mean_daily_tmax_c"] is not None]
station["longterm_hot_month_mean_daily_tmax_c"]=max(ok) if ok else None
station["meets_32C_exclusion"]=bool(max(ok)>=32.0) if len(ok)==12 else None
station["decision_note"]="Full 1991—2020 station monthly coverage only if 360 valid months. Observed 25yr partial averages diagnostic, not official 30-year climatological normal."
record={"created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"sites":rows,"jma_59981":station,
        "rule":"Mean of daily maximum temp in hottest month >=32C excludes; single anomalous month doesn't."}
(root/"phase1_island_climate_1991_2020_20261110.json").write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
with (root/"phase1_island_climate_1991_2020_20261110.csv").open("w",encoding="utf-8-sig",newline="") as f:
 writer=csv.writer(f);writer.writerow(["region","site","year/month","observed_59981_monthly_avg_daily_max","nasa_power_model_avg_daily_max","note"])
 for item in rows:
  for m in range(1,13):
   obs=mon[f"{m:02d}"]["mean_of_observed_monthly_mean_daily_tmax_c"] if "西沙" in item["region"] else ""
   v=item.get("monthlies",{}).get(f"{m:02d}",{}).get("model_tmax_daily_mean_c")
   writer.writerow([item["region"],item["site"],f"1991—2020 {m:02d}",obs,v,"JMA exact station observation 25+ years" if obs is not None and obs!="" else "coarse model reference only"])
print("RESULT",json.dumps({"jma_valid_months":len(jma_rows),"jma_hot_month":station["longterm_hot_month_mean_daily_tmax_c"],"jma_exclusion":station["meets_32C_exclusion"],"models":{r["region"]:r.get("model_hot_month_daily_tmax_mean_c") for r in rows},"errors":jma_error},ensure_ascii=False),flush=True)
