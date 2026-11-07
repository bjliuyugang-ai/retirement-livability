#!/usr/bin/env python3
"""National R2 first genuine sunshine, precipitation and humidity cascade.

Consumes existing 1991-2020 raw daily ERA5 for 12 historic point-joined counties
and the currently expanded R1 nationwide 2847-row roster. Never refetches.
Unscreened counties retain their unknown status, not excluded or formally graded.
"""
import csv,datetime,hashlib,json,pathlib,statistics
ROOT=pathlib.Path("research_engine/retirement")
OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
OLD_RAW=OUT/"archived_climate_42245826626"
IN_CSV=ROOT/"status/national_r1_expanded.csv"
IN_SUM=ROOT/"status/national_r1_expanded_summary.json"
R1_OLD=ROOT/"status/national_r1_first_real_batch_evidence.json"
MICRO=ROOT/"status/latest-microclimate-pilot.json"
def sha(x):return hashlib.sha256(x).hexdigest()
def longest(flags):
    n=m=0
    for ok in flags:
        n=n+1 if ok else 0;m=max(m,n)
    return m
r1=json.loads(IN_SUM.read_text(encoding="utf-8"))
prior=json.loads(R1_OLD.read_text(encoding="utf-8"))
micro=json.loads(MICRO.read_text(encoding="utf-8"))
if r1["cumulative_R1_point_data_counties"]<13 or r1["R1_carry_forward_to_R2"]!=2847:
    raise RuntimeError("No valid R1 national expansion prerequisite")
if prior["R1_real_point_evidence_counties"]!=12 or prior["R1_carry_forward_count"]!=2847:
    raise RuntimeError("Missing primary original 12 daily archive links")
with IN_CSV.open(encoding="utf-8-sig",newline="") as f:
    dr=csv.DictReader(f);cols=list(dr.fieldnames);rows=list(dr)
if len(rows)!=2847 or len({x["candidate_code"] for x in rows})!=2847:
    raise RuntimeError("R1 national register changed")
bycode={x["candidate_code"]:x for x in rows}
byhum={x["site"]:x for x in micro["points"]}
fields=["R2_evidence_scope","R2_annual_sunshine_hours","R2_winter_nov_mar_mean_daily_sunshine_hours",
 "R2_annual_rainfall_mm","R2_rain_ge1_days_per_year","R2_longest_rain_spell_days",
 "R2_longest_less_than_one_hour_sunshine_spell_days","R2_model_relative_humidity_annual_pct",
 "R2_model_summer_dewpoint_c","R2_preference_signal","R2_raw_sha256",
 "R2_evidence_source","R2_missing_parameters"]
for k in fields:
    if k in cols:raise RuntimeError("R2 fields already present: "+k)
cols+=fields
records=[]
for old in prior["county_era5_climate_records"]:
    site=old["site"];code=old["candidate_county_code"]
    rawpath=list(OLD_RAW.rglob(site+".json"))
    if len(rawpath)!=1:raise RuntimeError("Raw ERA5 archive missing "+site)
    raw=rawpath[0].read_bytes()
    if sha(raw)!=old["raw_daily_sha256"]:raise RuntimeError("Original R1 raw digest mismatch "+site)
    data=json.loads(raw)["daily"]
    dates=data["time"];sun=data["sunshine_duration"];rain=data["precipitation_sum"]
    if len(dates)!=10958 or dates[0]!="1991-01-01" or dates[-1]!="2020-12-31":
        raise RuntimeError("Invalid raw daily period")
    if sum(z is not None for z in sun)<.99*len(sun) or sum(z is not None for z in rain)<.99*len(rain):
        raise RuntimeError("Missing sun/rain >1% "+site)
    valid_sun=[float(x) for x in sun if x is not None]
    valid_rain=[float(x) for x in rain if x is not None]
    winter=[float(x) for day,x in zip(dates,sun) if x is not None and int(day[5:7]) in {11,12,1,2,3}]
    wet_flags=[x is not None and float(x)>=1 for x in rain]
    low_sun_flags=[x is not None and float(x)<3600 for x in sun]
    metrics={"annual_sunshine_hours":round(sum(valid_sun)/3600/30,2),
        "winter_nov_mar_mean_daily_sunshine_hours":round(statistics.mean(winter)/3600,3),
        "annual_precipitation_mm":round(sum(valid_rain)/30,2),
        "rain_ge1_days_per_year":round(sum(wet_flags)/30,2),
        "longest_rain_ge1_spell_days_in_30y":longest(wet_flags),
        "longest_less_than_one_hour_sun_spell_days_in_30y":longest(low_sun_flags)}
    h=byhum[site];hm=h.get("humidity_era5")
    if hm and h["humidity_status"]=="EXPLORATORY_DATA_LOADED":
        metrics["annual_humidity_relative_pct"]=hm["mean_relative_humidity_2m_mean"]
        metrics["summer_mean_dewpoint_c"]=hm["summer_dew_point_2m_mean"]
    else:
        metrics["annual_humidity_relative_pct"]=None
        metrics["summer_mean_dewpoint_c"]=None
    match_sun=metrics["annual_sunshine_hours"]>=2200
    match_rain=metrics["annual_precipitation_mm"]<=1000
    match_hum=(50<=metrics["annual_humidity_relative_pct"]<=70) if metrics["annual_humidity_relative_pct"] is not None else None
    signal="POINT_PREFERENCE_PARTIAL_MATCH" if any(x is True for x in [match_sun,match_rain,match_hum]) else "POINT_PREFERENCE_CONFLICTS_OR_UNKNOWN"
    c=bycode[code]
    if c["R2_status"]!="NOT_SCREENED":raise RuntimeError("R2 already processed "+site)
    c["R2_status"]="SCANNED_SUN_RAIN_POINT_HUMIDITY_PARTIAL" if hm else "SCANNED_SUN_RAIN_POINT_HUMIDITY_MISSING"
    c["R2_evidence_scope"]="MODEL_POINT_NOT_COUNTY_OR_RESIDENCE"
    c["R2_annual_sunshine_hours"]=metrics["annual_sunshine_hours"]
    c["R2_winter_nov_mar_mean_daily_sunshine_hours"]=metrics["winter_nov_mar_mean_daily_sunshine_hours"]
    c["R2_annual_rainfall_mm"]=metrics["annual_precipitation_mm"]
    c["R2_rain_ge1_days_per_year"]=metrics["rain_ge1_days_per_year"]
    c["R2_longest_rain_spell_days"]=metrics["longest_rain_ge1_spell_days_in_30y"]
    c["R2_longest_less_than_one_hour_sunshine_spell_days"]=metrics["longest_less_than_one_hour_sun_spell_days_in_30y"]
    c["R2_model_relative_humidity_annual_pct"]=metrics["annual_humidity_relative_pct"] if hm else ""
    c["R2_model_summer_dewpoint_c"]=metrics["summer_mean_dewpoint_c"] if hm else ""
    c["R2_preference_signal"]=signal
    c["R2_raw_sha256"]=sha(raw)
    c["R2_evidence_source"]="2026-11-06-archived-ERA5-1991-2020/"+site+".json"
    c["R2_missing_parameters"]="INDEPENDENT_CMA_1991_2020_STATION;SITE_LEVEL_REPRESENTATIVENESS;HUMIDITY" if not hm else "INDEPENDENT_CMA_1991_2020_STATION;SITE_LEVEL_REPRESENTATIVENESS"
    c["cascade_status"]="ACTIVE_PENDING"
    c["last_completed_round"]="R2_POINT_PRELIMINARY"
    c["missing_parameter_list"]="R1_R2_RESIDENTIAL_REPRESENTATIVENESS_AND_CMA_OPEN;R3_R5_UNSCANNED;OFFICIAL_2026_ID_OPEN"
    records.append({"site":site,"code":code,"name":c["candidate_name"],"metrics":metrics,
        "R2_sunshine_ideal_met":match_sun,"R2_rain_ideal_met":match_rain,"R2_humidity_ideal_met":match_hum,
        "source_raw_sha256":sha(raw),"source_original_run_id":"42245826626",
        "humidity_source":"research_engine/retirement/status/latest-microclimate-pilot.json" if hm else None,
        "formal_county_rating_authorized":False})
n=sum(x["R2_status"].startswith("SCANNED_") for x in rows)
unscanned=sum(x["R2_status"]=="NOT_SCREENED" for x in rows)
if n!=12 or unscanned!=2835 or any(x["confirmed_exit_round"] for x in rows):raise RuntimeError("R2 counts or exit corruption")
if any(x["valid_county_screening"].lower()=="true" for x in rows):
    raise RuntimeError("Official grade contamination")
p=OUT/"national_r2_first_real_batch.csv"
with p.open("w",encoding="utf-8-sig",newline="") as f:
    w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(rows)
result={"schema":"RET_NATIONAL_R2_FIRST_12_REAL_SUN_RAIN_HUMIDITY_V1",
 "generated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "R1_national_register_sha256":sha(IN_CSV.read_bytes()),
 "input_county_candidates":2847,"R1_carry_forward":2847,
 "R1_points_with_real_temperature":r1["cumulative_R1_point_data_counties"],
 "R1_unscanned":r1["R1_not_scanned"],
 "R2_county_point_sun_rain_scanned":12,
 "R2_humidity_model_sites":sum(x["metrics"]["annual_humidity_relative_pct"] is not None for x in records),
 "R2_unscanned":2835,"R2_verified_exclusions":0,"R2_carry_forward":2847,
 "formal_valid_county_screenings":0,"formal_grade_changes":0,
 "point_records":records,"CSV_sha256":sha(p.read_bytes()),
 "limitations":["ERA5 model seasonal sun/rain does not replace independent CMA station normals",
   "No county-wide or residential site spatial representation verified",
   "R1 source county codes are historical name matches, not 2026 official certification",
   "Unscanned / unmeasured counties remain eligible for next parameter round",
   "Long consecutive spells are the maximum during 30 years, not a typical annual spell"]}
(OUT/"national_r2_first_real_batch_evidence.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"R2_scanned_point_counties":n,"humidity_sites":result["R2_humidity_model_sites"],
 "R2_unscanned":unscanned,"carry_forward":2847,"R1_point_temperature_evidence":result["R1_points_with_real_temperature"],
 "formal_county_screenings":0},ensure_ascii=False),flush=True)
