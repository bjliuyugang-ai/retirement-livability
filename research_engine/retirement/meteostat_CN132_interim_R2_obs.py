#!/usr/bin/env python3
"""Actual 1991-2020 source-filtered Meteostat rain and sunshine expansion for
132 GIS-consistent but short-history Chinese meteorological stations.

This is explicit INTERIM PARTIAL R2 evidence (>=180 observation months and >=10
per calendar month), NOT a 30-year climate normal; keep 73 prior longer source
R2 county candidates unchanged. Every category keeps unknowns and original
source IDs, no exclusion or formal grading.
"""
import collections,csv,datetime,hashlib,json,pathlib,urllib.request
import duckdb
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
STA=ROOT/"status/meteostat_CN_226_R1_tiered_expansion_evidence.json"
PREV=ROOT/"status/national_R1_226_obs_station_quality_tiers_2847.csv"
S=ROOT/"status/meteostat_CN_1991_2020_station_candidate_normals.json"
D=OUT/"meteostat_bulk_runtime";D.mkdir(parents=True,exist_ok=True)
def digest(b):return hashlib.sha256(b).hexdigest()
def load(p):return json.loads(p.read_text(encoding="utf-8"))
st=load(STA);src=load(S)
if not(st["interim_stations_spatially_accepted"]==132 and
 st["new_interim_only_candidate_counties"]==127 and
 st["strict_long_period_or_ERA5_prior_R1_counties_unchanged"]==87 and
 st["R1_counties_with_any_real_point_including_short_history"]==214 and
 st["R2_old_partial_counties_unchanged"]==73):
 raise RuntimeError("Wrong V1.6 prior station tier")
if digest(PREV.read_bytes())!=st["output_national_csv_sha256"]:
 raise RuntimeError("National R1 interim input CSV checksum drift")
with PREV.open(encoding="utf-8-sig",newline="") as f:
 rdr=csv.DictReader(f);fields=list(rdr.fieldnames);rows=list(rdr)
bycode={r["candidate_code"]:r for r in rows}
if len(rows)!=2847 or len(bycode)!=2847:raise RuntimeError("R0 national candidate count changed")
prior_R2={z["candidate_code"] for z in rows if z["R2_status"]!="NOT_SCREENED"}
if len(prior_R2)!=73:raise RuntimeError("Frozen prior longer source R2 73 count changed")
station_details=[z for z in st["station_details"] if z["accept_for_interim_partial_R1"]]
stationmap={str(z["station_id"]):z for z in station_details}
if len(stationmap)!=132 or len({z["coded_candidate_code"] for z in station_details})!=131:
 raise RuntimeError("Interim GIS accepted station IDs / unique counties mismatch; 150782 has 2 stations")
mp=D/"monthly.parquet"
expected=src["source_sha256"]["monthly_parquet"]
if not mp.exists() or digest(mp.read_bytes())!=expected:
 if mp.exists():mp.unlink()
 u="https://data.meteostat.net/monthly.parquet"
 req=urllib.request.Request(u,headers={"User-Agent":"RetirementCNInterimR2ObsSource/1.0"})
 with urllib.request.urlopen(req,timeout=170) as rr,mp.open("wb") as f:
  while True:
   piece=rr.read(1048576)
   if not piece:break
   f.write(piece)
 if digest(mp.read_bytes())!=expected:raise RuntimeError("Monthly source parquet changed: cannot compare to frozen source")
con=duckdb.connect(":memory:")
con.execute("CREATE TABLE stationIDs (sid VARCHAR)")
con.executemany("INSERT INTO stationIDs VALUES (?)",[(z,) for z in stationmap])
schema={z[0] for z in con.execute("DESCRIBE SELECT * FROM read_parquet(?)",[str(mp)]).fetchall()}
if not {"station","date","prcp","prcp_source","tsun","tsun_source"}.issubset(schema):
 raise RuntimeError("Monthly source lacks independent parameter provenance")
obs=con.execute("""SELECT CAST(a.station AS VARCHAR),CAST(a.date AS DATE),
  CAST(a.prcp AS DOUBLE), CAST(a.prcp_source AS VARCHAR),
  CAST(a.tsun AS DOUBLE), CAST(a.tsun_source AS VARCHAR)
  FROM read_parquet(?) a JOIN stationIDs b
  ON CAST(a.station AS VARCHAR)=b.sid
  WHERE a.date BETWEEN DATE '1991-01-01' AND DATE '2020-12-31'
  ORDER BY a.station,a.date""",[str(mp)]).fetchall()
grouped=collections.defaultdict(list)
for sid,dt,precip,sourcep,sun,sourcesun in obs:grouped[sid].append((dt,precip,sourcep,sun,sourcesun))
acceptedProviders={"ghcnd","climat","isd_lite","metar","dwd_hourly","dwd_daily"}
def observed(source):
 if source is None:return False
 p=str(source).lower().split()
 return bool(p) and all(z in acceptedProviders for z in p)
def parameter_months(items,source_position,value_position,valid):
 result=collections.defaultdict(list);providers=collections.Counter();rejected=collections.Counter();calendar=set()
 for r in items:
  dt=r[0];value=r[value_position];source=r[source_position]
  if value is None:continue
  if valid(float(value)) and observed(source):
   key=(dt.year,dt.month)
   if key in calendar:raise RuntimeError("Duplicate station monthly data for "+str(key))
   calendar.add(key)
   result[dt.month].append(float(value))
   providers[str(source)]+=1
  else:rejected[str(source)]+=1
 total=sum(len(z) for z in result.values())
 sufficient=total>=180 and all(len(result[m])>=10 for m in range(1,13))
 counts={str(m):len(result[m]) for m in range(1,13)}
 return result,counts,total,sufficient,dict(providers),dict(rejected)
results=[]
for sid,p in sorted(stationmap.items()):
 items=grouped.get(sid,[])
 p_m,p_by,p_n,p_ok,p_prov,p_bad=parameter_months(items,2,1,lambda x:0<=x<=5000)
 t_m,t_by,t_n,t_ok,t_prov,t_bad=parameter_months(items,4,3,lambda x:0<=x<=44640)
 def rough_available_month_year_avg(series,unit):
  if not all(series[m] for m in range(1,13)):return None
  return round(sum(sum(series[m])/len(series[m]) for m in range(1,13))/unit,2)
 z={"station_id":sid,"candidate_code":p["coded_candidate_code"],
  "candidate_name":p["coded_candidate_name"],
  "source_r1_recorded_tmax_tmin_months":p["obs_month_count_in_1991_2020_range"],
  "R2_observation_precip_months":p_n,"R2_observation_sunshine_months":t_n,
  "R2_precip_by_month_count":p_by,"R2_sunshine_by_month_count":t_by,
  "R2_precip_ge180mo_every_month10years":p_ok,
  "R2_sunshine_ge180mo_every_month10years":t_ok,
  "R2_precip_rough_annual_mm_during_available_years":rough_available_month_year_avg(p_m,1) if p_ok else None,
  "R2_sunshine_rough_annual_hours_during_available_years":rough_available_month_year_avg(t_m,60) if t_ok else None,
  "R2_precip_providers":p_prov,"R2_sunshine_providers":t_prov,
  "R2_rejected_precip_sources":p_bad,"R2_rejected_sunshine_sources":t_bad,
  "full30year_R2_normal_proven":False,
  "2026_official_county_identity_proven":False,
  "residential_R2_conditions_proven":False}
 results.append(z)
if len(results)!=132:raise RuntimeError("R2 source station matches not complete")
passed=[z for z in results if z["R2_precip_ge180mo_every_month10years"] or z["R2_sunshine_ge180mo_every_month10years"]]
bycounty_all=collections.defaultdict(list)
for z in passed:bycounty_all[z["candidate_code"]].append(z)
# Never blend temperatures/precipitation of distinct stations. Choose one record
# with the most independently qualified R2 parameters; tie by total observed months.
def station_rank(z):
 return (int(z["R2_precip_ge180mo_every_month10years"])+int(z["R2_sunshine_ge180mo_every_month10years"]),
   z["R2_observation_precip_months"]+z["R2_observation_sunshine_months"],z["station_id"])
bycounty={code:sorted(records,key=station_rank,reverse=True)[0] for code,records in bycounty_all.items()}
multi_station_all=collections.defaultdict(list)
for z in results:multi_station_all[z["candidate_code"]].append(z["station_id"])
multi_station_codes={code:sorted(ids) for code,ids in multi_station_all.items() if len(ids)>1}
if multi_station_codes!={"150782":["50434","50632"]}:
 raise RuntimeError("Unexpected 132-station duplicate county mapping "+str(multi_station_codes))
new=sorted(set(bycounty)-prior_R2)
extra=["R2_short_history_obs_station_id","R2_short_history_precip_months",
 "R2_short_history_sunshine_months","R2_short_history_precip_rough_annual_mm",
 "R2_short_history_sunshine_rough_annual_hours","R2_short_history_precip_source_status",
 "R2_short_history_sunshine_source_status","R2_short_history_all30years_unverified"]
for k in extra:
 if k in fields:raise RuntimeError("R2 short source column unexpectedly already exists "+k)
fields+=extra
for code,z in bycounty.items():
 r=bycode[code]
 r["R2_short_history_obs_station_id"]=z["station_id"]
 r["R2_short_history_precip_months"]=z["R2_observation_precip_months"]
 r["R2_short_history_sunshine_months"]=z["R2_observation_sunshine_months"]
 r["R2_short_history_precip_rough_annual_mm"]=z["R2_precip_rough_annual_mm_during_available_years"] if z["R2_precip_ge180mo_every_month10years"] else ""
 r["R2_short_history_sunshine_rough_annual_hours"]=z["R2_sunshine_rough_annual_hours_during_available_years"] if z["R2_sunshine_ge180mo_every_month10years"] else ""
 r["R2_short_history_precip_source_status"]="OBS_180MO_MIN10YR_PER_CALENDAR_MONTH" if z["R2_precip_ge180mo_every_month10years"] else "UNKNOWN_NOT_OBS_180MO"
 r["R2_short_history_sunshine_source_status"]="OBS_180MO_MIN10YR_PER_CALENDAR_MONTH" if z["R2_sunshine_ge180mo_every_month10years"] else "UNKNOWN_NOT_OBS_180MO"
 r["R2_short_history_all30years_unverified"]="TRUE"
 if code in new:
  if r["R2_status"]!="NOT_SCREENED":raise RuntimeError("New R2 already assigned longer baseline")
  r["R2_status"]="INTERIM_SHORT_OBS_RAIN_AND_SUN" if z["R2_precip_ge180mo_every_month10years"] and z["R2_sunshine_ge180mo_every_month10years"] else ("INTERIM_SHORT_OBS_RAIN_ONLY" if z["R2_precip_ge180mo_every_month10years"] else "INTERIM_SHORT_OBS_SUN_ONLY")
  r["R2_evidence_scope"]="REAL_OBS_MONTHLY_SHORTER_THAN_30Y_WINDOW_PENDING_FULL_1991_2020"
  r["R2_missing_parameters"]="FULL_30YEAR_NORMAL;CONSECUTIVE_RAINY_DAYS;SUNLESS_DAYS;RESIDENCE_AND_OFFICIAL_COUNTY_QA"
  r["last_completed_round"]="R2_SHORT_HISTORY_INTERIM_PARTIAL"
  r["cascade_status"]="ACTIVE_PENDING"
  r["missing_parameter_list"]=(r["missing_parameter_list"] or "")+";R2_30YEAR_SOURCE_BASELINE_NOT_MET"
after=sum(r["R2_status"]!="NOT_SCREENED" for r in rows)
if after!=73+len(new):raise RuntimeError("New R2 tiered evidence total mismatch")
if any(r["confirmed_exit_round"] for r in rows) or any(str(r["valid_county_screening"]).lower()=="true" for r in rows):
 raise RuntimeError("No formal screen and no confirmed exclusion permitted")
outcsv=OUT/"national_R2_132_interim_obs_source_2847.csv"
with outcsv.open("w",encoding="utf-8-sig",newline="") as f:
 wr=csv.DictWriter(f,fieldnames=fields);wr.writeheader();wr.writerows(rows)
stationcsv=OUT/"meteostat_CN132_interim_R2_parameter_source.csv"
fields2=["station_id","candidate_code","candidate_name","source_r1_recorded_tmax_tmin_months",
 "R2_observation_precip_months","R2_observation_sunshine_months",
 "R2_precip_ge180mo_every_month10years","R2_sunshine_ge180mo_every_month10years",
 "R2_precip_rough_annual_mm_during_available_years",
 "R2_sunshine_rough_annual_hours_during_available_years",
 "R2_precip_providers","R2_sunshine_providers"]
with stationcsv.open("w",encoding="utf-8-sig",newline="") as f:
 wr=csv.DictWriter(f,fieldnames=fields2);wr.writeheader()
 for z in results:
  row={k:z[k] for k in fields2}
  row["R2_precip_providers"]=json.dumps(row["R2_precip_providers"],ensure_ascii=False)
  row["R2_sunshine_providers"]=json.dumps(row["R2_sunshine_providers"],ensure_ascii=False)
  wr.writerow(row)
report={"schema":"RET_CN132_R2_SOURCE_INDEPENDENT_1991_2020_INTERIM_V1",
 "created_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "source_parquet_sha256":expected,"source_station_R1_tier_evidence_sha256":digest(STA.read_bytes()),
 "input_provisional_counties":2847,"interim_station_geographic_accepted":132,
 "interim_R2_precip_observation_sufficient_stations":sum(z["R2_precip_ge180mo_every_month10years"] for z in results),
 "interim_R2_sunshine_observation_sufficient_stations":sum(z["R2_sunshine_ge180mo_every_month10years"] for z in results),
 "interim_R2_stations_with_any_parameter_evidence":len(passed),
 "interim_R2_distinct_counties_with_any_parameter_evidence":len(bycounty),
 "multi_station_candidate_codes_with_both_station_ids":multi_station_codes,
 "multi_station_station_selection_rule":"one primary per county chosen by number of sufficient parameters and observed-month counts; retain all original station-level source records, never average the two stations",
 "new_interim_only_R2_counties":len(new),"new_interim_R2_codes":new,
 "prior_R2_longer_source_partials_retained":73,
 "R2_total_counties_any_partial_evidence_including_interim":after,
 "R2_never_scanned_or_without_any_observation":2847-after,
 "R1_long_source_partials_retained":87,
 "R1_short_history_extra_partials_retained":127,
 "R1_all_partial_any_period_retained":214,
 "formal_valid_county_screenings":0,"confirmed_exclusions":0,
 "relevant_source_provider_families":sorted(acceptedProviders),
 "interim_not_full_1991_2020_climate_normal":True,
 "station_parameter_results":results,
 "national_output_csv_sha256":digest(outcsv.read_bytes()),
 "station_source_csv_sha256":digest(stationcsv.read_bytes()),
 "limitations":[">=180 months and >=10 per calendar month is only discovery-tier observed source, NOT 30-year CMA normal",
 "Observation-source vetted separately for precipitation and sunshine, model substitutes/rejected sources cannot count",
 "Computed annual figure is descriptive from available years; sampling bias and recent climate drift uncorrected",
 "All climate suitability thresholds and A/B/C/D withheld, missing parameters remain pending, no county eliminated"]}
out=OUT/"meteostat_CN132_interim_R2_evidence.json"
out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:report[k] for k in ["interim_station_geographic_accepted",
 "interim_R2_precip_observation_sufficient_stations",
 "interim_R2_sunshine_observation_sufficient_stations",
 "interim_R2_stations_with_any_parameter_evidence","new_interim_only_R2_counties",
 "prior_R2_longer_source_partials_retained",
 "R2_total_counties_any_partial_evidence_including_interim",
 "R2_never_scanned_or_without_any_observation"]},ensure_ascii=False),flush=True)
