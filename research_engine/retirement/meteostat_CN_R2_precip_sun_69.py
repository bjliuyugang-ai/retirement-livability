#!/usr/bin/env python3
"""R2 actual observational monthly precipitation and sunshine from Meteostat
1991–2020 bulk source, joined ONLY to coded-county GIS-accepted stations.

Sources are per-PARAMETER; do not count model gap-fills. Monthly prcp is total
mm, tsun monthly sunshine minutes (Meteostat documentation).
A valid partial R2 parameter requires >=300 1991-2020 monthly observations
AND >=20 per calendar month. A precipitation-only county is partial R2 evidence,
NOT a passed sunshine or humidity/climate stage.
"""
import collections,csv,datetime,hashlib,json,pathlib,sqlite3,urllib.request
import duckdb
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
S=ROOT/"status/meteostat_CN_1991_2020_station_candidate_normals.json"
C=ROOT/"status/meteostat_70_station_coded_county_spatial_QA.json"
PREV=ROOT/"status/national_R1_meteostat_coded_county_candidate_overlay_2847.csv"
DATA=OUT/"meteostat_bulk_runtime";DATA.mkdir(parents=True,exist_ok=True)
URL="https://data.meteostat.net/monthly.parquet"
def sha(b):return hashlib.sha256(b).hexdigest()
s=json.loads(S.read_text(encoding="utf-8"));c=json.loads(C.read_text(encoding="utf-8"))
if c["station_provisional_code_geoposition_and_name_accepted"]!=69 or c["new_provisional_counties_with_station_point_temperature"]!=65 or c["total_provisional_counties_with_any_R1_point_temperature"]!=87:
 raise RuntimeError("R1 code polygon prerequisite not verified")
if sha(PREV.read_bytes())!=c["output_national_overlay_csv_sha256"]:raise RuntimeError("R1 full ledger source digest drift")
path=DATA/"monthly.parquet"
expected=s["source_sha256"]["monthly_parquet"]
if not path.exists() or sha(path.read_bytes())!=expected:
 if path.exists():path.unlink()
 req=urllib.request.Request(URL,headers={"User-Agent":"RET_CN_1991_2020_R2_OBSERVATIONAL_BULK/1.0"})
 with urllib.request.urlopen(req,timeout=150) as rr,path.open("wb") as f:
  while True:
   chunk=rr.read(1024*1024)
   if not chunk:break
   f.write(chunk)
 if sha(path.read_bytes())!=expected:raise RuntimeError("Meteostat monthly source changed; needs provenance snapshot recompute")
print("SOURCE_PARQUET_SHA256_PASS",expected,flush=True)
with PREV.open(encoding="utf-8-sig",newline="") as f:
 r=csv.DictReader(f);cols=list(r.fieldnames);rows=list(r)
bycode={x["candidate_code"]:x for x in rows}
if len(rows)!=2847 or len(bycode)!=2847:raise RuntimeError("R1 provisional roster count changed")
accepted=[x for x in c["station_records"] if x["can_add_county_R1_station_evidence"]]
ids={str(x["station_id"]) for x in accepted}
if len(ids)!=69:raise RuntimeError("More than one station id in accepted code associations")
code_by_id={str(x["station_id"]):x["2026_candidate_county_code"] for x in accepted}
duck=duckdb.connect(":memory:")
duck.execute("CREATE TABLE input_stations(station_id VARCHAR)")
duck.executemany("INSERT INTO input_stations VALUES (?)",[(z,) for z in ids])
schema={x[0] for x in duck.execute("DESCRIBE SELECT * FROM read_parquet(?)",[str(path)]).fetchall()}
needed={"station","date","prcp","prcp_source","tsun","tsun_source"}
if not needed.issubset(schema):raise RuntimeError("Missing monthly source columns "+str(needed-schema))
data=duck.execute("""SELECT CAST(a.station AS VARCHAR),a.date,a.prcp,a.prcp_source,a.tsun,a.tsun_source
 FROM read_parquet(?) a JOIN input_stations b ON CAST(a.station AS VARCHAR)=b.station_id
 WHERE a.date BETWEEN DATE '1991-01-01' AND DATE '2020-12-31' ORDER BY a.station,a.date""",[str(path)]).fetchall()
if not data:raise RuntimeError("No real R2 monthly data from station source")
grouped=collections.defaultdict(list)
for station,dt,precip,ps,sun,ss in data:
 grouped[station].append((dt,precip,ps,sun,ss))
providers={"ghcnd","climat","isd_lite","metar","dwd_hourly","dwd_daily"}
def accepted_obs(source):
 if source is None:return False
 parts=str(source).lower().split()
 return bool(parts) and all(part in providers for part in parts)
def calc(stationid):
 entries=grouped.get(stationid,[])
 mon_precip=collections.defaultdict(list);mon_sun=collections.defaultdict(list)
 src_precip=collections.Counter();src_sun=collections.Counter()
 bad_precip=collections.Counter();bad_sun=collections.Counter()
 for date,p,ps,ts,ss in entries:
  month=date.month
  if p is not None and 0<=float(p)<=5000 and accepted_obs(ps):
   mon_precip[month].append(float(p));src_precip[str(ps)]+=1
  elif p is not None:bad_precip[str(ps)]+=1
  if ts is not None and 0<=float(ts)<=31*24*60 and accepted_obs(ss):
   mon_sun[month].append(float(ts));src_sun[str(ss)]+=1
  elif ts is not None:bad_sun[str(ss)]+=1
 nprecip=sum(len(x) for x in mon_precip.values())
 nsun=sum(len(x) for x in mon_sun.values())
 prec_ok=nprecip>=300 and all(len(mon_precip[m])>=20 for m in range(1,13))
 sun_ok=nsun>=300 and all(len(mon_sun[m])>=20 for m in range(1,13))
 def mean_annual(mdict,unit):
  return round(sum(sum(mdict[m])/len(mdict[m]) for m in range(1,13))/unit,2)
 # Winter Nov-Mar average sunshine/day; weighted month climatology.
 wintermonths=[11,12,1,2,3]
 mdays={1:31,2:28.25,3:31,4:30,5:31,6:30,7:31,8:31,9:30,10:31,11:30,12:31}
 winter_sun_day=round(sum((sum(mon_sun[m])/len(mon_sun[m]))/60 for m in wintermonths)/sum(mdays[m] for m in wintermonths),3) if sun_ok else None
 return {"station_id":stationid,"candidate_county_code":code_by_id[stationid],
 "raw_station_monthly_rows":len(entries),"precip_obs_source_months":nprecip,
 "sunshine_obs_source_months":nsun,"precip_n_by_month":{str(m):len(mon_precip[m]) for m in range(1,13)},
 "sun_n_by_month":{str(m):len(mon_sun[m]) for m in range(1,13)},
 "precip_source_providers":dict(src_precip),"sunshine_source_providers":dict(src_sun),
 "precip_rejected_source_counts":dict(bad_precip),"sunshine_rejected_source_counts":dict(bad_sun),
 "precip_300months_and_20_eachmonth_pass":prec_ok,
 "sun_300months_and_20_eachmonth_pass":sun_ok,
 "mean_annual_precip_mm":mean_annual(mon_precip,1) if prec_ok else None,
 "mean_annual_sunshine_hours":mean_annual(mon_sun,60) if sun_ok else None,
 "winter_nov_mar_daily_sunshine_hours":winter_sun_day,
 "rainy_days_or_extreme_spells_computed":False,
 "2026_official_county_verified":False,
 "station_to_residence_qualified":False}
results=[calc(sid) for sid in sorted(ids)]
bycounty=collections.defaultdict(list)
for z in results:bycounty[z["candidate_county_code"]].append(z)
extra=["R2_meteostat_station_id","R2_meteostat_precip_months","R2_meteostat_sun_months",
 "R2_meteostat_precip_1991_2020_mm","R2_meteostat_annual_sunshine_hours",
 "R2_meteostat_winter_nov_mar_sun_per_day_hours",
 "R2_meteostat_precip_sufficiency","R2_meteostat_sun_sufficiency","R2_meteostat_partial_source_quality"]
for field in extra:
 if field in cols:raise RuntimeError("R2 column already exists "+field)
cols+=extra
new_count=0;retain_count=0
for code,cs in bycounty.items():
 row=bycode[code]
 # Distinct 69 sources crosswalk currently one station per county; don't assume forever.
 if len(cs)!=1:raise RuntimeError("Multiple stations in one candidate county require explicit aggregation QA "+code)
 z=cs[0]
 row["R2_meteostat_station_id"]=z["station_id"]
 row["R2_meteostat_precip_months"]=z["precip_obs_source_months"]
 row["R2_meteostat_sun_months"]=z["sunshine_obs_source_months"]
 row["R2_meteostat_precip_1991_2020_mm"]=z["mean_annual_precip_mm"] if z["mean_annual_precip_mm"] is not None else ""
 row["R2_meteostat_annual_sunshine_hours"]=z["mean_annual_sunshine_hours"] if z["mean_annual_sunshine_hours"] is not None else ""
 row["R2_meteostat_winter_nov_mar_sun_per_day_hours"]=z["winter_nov_mar_daily_sunshine_hours"] if z["winter_nov_mar_daily_sunshine_hours"] is not None else ""
 row["R2_meteostat_precip_sufficiency"]="PASS" if z["precip_300months_and_20_eachmonth_pass"] else "INSUFFICIENT"
 row["R2_meteostat_sun_sufficiency"]="PASS" if z["sun_300months_and_20_eachmonth_pass"] else "INSUFFICIENT"
 has=z["precip_300months_and_20_eachmonth_pass"] or z["sun_300months_and_20_eachmonth_pass"]
 row["R2_meteostat_partial_source_quality"]="OBS_SOURCE_VETTED_PARTIAL" if has else "DATA_INSUFFICIENT_REMAIN_UNKNOWN"
 if has:
  if row["R2_status"]=="NOT_SCREENED":
   status=("STATION_OBS_PRECIP_AND_SUN_PARTIAL" if z["precip_300months_and_20_eachmonth_pass"] and z["sun_300months_and_20_eachmonth_pass"] else
       "STATION_OBS_PRECIP_PARTIAL_SUN_UNKNOWN" if z["precip_300months_and_20_eachmonth_pass"] else
       "STATION_OBS_SUN_PARTIAL_PRECIP_UNKNOWN")
   row["R2_status"]=status
   row["R2_evidence_scope"]="OBS_STATION_MONTHLY_NOT_2026_RESIDENTIAL_COUNTY"
   row["R2_missing_parameters"]="DAILY_CONSECUTIVE_RAINY_DAYS;CONTINUOUS_WET_COLD;RESIDENTIAL_MICROCLIMATE;2026_OFFICIAL_CODE"
   row["cascade_status"]="ACTIVE_PENDING"
   row["last_completed_round"]="R2_STATION_PARTIAL"
   new_count+=1
  else:retain_count+=1
before=12
after=sum(x["R2_status"]!="NOT_SCREENED" for x in rows)
if after!=before+new_count:raise RuntimeError("R2 true count mismatch before "+str(before)+" after "+str(after)+" new "+str(new_count))
if any(x["confirmed_exit_round"] for x in rows) or any(str(x["valid_county_screening"]).lower()=="true" for x in rows):
 raise RuntimeError("No full screening or confirmed fatal exclusion is allowed")
csvout=OUT/"national_R2_meteostat_station_source_2847.csv"
with csvout.open("w",encoding="utf-8-sig",newline="") as f:
 wr=csv.DictWriter(f,fieldnames=cols);wr.writeheader();wr.writerows(rows)
precipstations=sum(z["precip_300months_and_20_eachmonth_pass"] for z in results)
sunstations=sum(z["sun_300months_and_20_eachmonth_pass"] for z in results)
report={"schema":"RET_NATIONAL_R2_CN_MSTA_OBS_PRECIP_SUN_1991_2020_V1",
 "created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "station_longmonthly_source_url":URL,"source_parquet_sha256":expected,
 "station_to_county_QA_sha256":sha(C.read_bytes()),"source_R1_national_CSV_sha256":sha(PREV.read_bytes()),
 "input_provisional_counties":2847,"coded_location_name_station_count":69,
 "station_monthly_rows_read":len(data),"precip_300month_observation_stations":precipstations,
 "sunshine_300month_observation_stations":sunstations,
 "stations_meeting_at_least_one_R2_observation_parameter":sum(z["precip_300months_and_20_eachmonth_pass"] or z["sun_300months_and_20_eachmonth_pass"] for z in results),
 "R2_original_partial_sites":12,
 "R2_new_station_partial_counties":new_count,
 "R2_prior_record_also_station_supported":retain_count,
 "R2_total_partial_site_counties":after,
 "R2_not_scanned_counties":2847-after,"carry_forward":2847,
 "confirmed_exclusions":0,"formal_valid_county_screenings":0,
 "official_2026_county_roster_verified":False,
 "source_accepted_only":["ghcnd","climat","isd_lite","metar","dwd_hourly","dwd_daily"],
 "source_rejected_if_contains":["dwd_mosmix","unknown","any NULL source"],
 "monthly_precipitation_units":"mm per month, mean annual from 12 monthly means",
 "monthly_sunshine_units":"minutes per month, mean annual converted to hours",
 "wind_humidity_and_rain_day_spells_evaluated":False,
 "all_station_parameter_results":results,"CSV_sha256":sha(csvout.read_bytes()),
 "limitations":["Each parameter independent 300-month and >=20-per-calendar-month source QA",
 "Missing sunshine does not block precipitation evidence but is still unknown",
 "Station point data does not show dwelling climate or boundary-current legal status",
 "Any county with source insufficiency remains R2 NOT_SCREENED if it had no previous R2",
 "No 2026 official county grade or climate fatal exclusions"]}
out=OUT/"national_R2_meteostat_station_source_evidence.json"
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["station_monthly_rows_read","precip_300month_observation_stations","sunshine_300month_observation_stations","stations_meeting_at_least_one_R2_observation_parameter","R2_new_station_partial_counties","R2_total_partial_site_counties","R2_not_scanned_counties"]},ensure_ascii=False),flush=True)
