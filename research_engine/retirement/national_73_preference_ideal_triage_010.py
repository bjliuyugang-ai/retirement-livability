#!/usr/bin/env python3
"""73 longer-history dual-R1/R2 climate point source preference triage.

Compare actual station source (monthly Tmax, precipitation, sunshine) or
ERA5 gridded point source against FROZEN non-fatal Master V1.2 preferences.
Do not merge same-name model and station data without labeling both.
Never infer residential conditions, hard health exclusions, approved formal
A/B/C/D grades, nor residence elevation from a station.
"""
import collections,csv,datetime,hashlib,json,pathlib
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/"status/national_R1R2_joint_2847_evidence_and_missingness.csv"
SUM=ROOT/"status/national_R1R2_joint_missingness_evidence.json"
R1SOURCE=ROOT/"status/meteostat_CN_226_R1_tiered_expansion_evidence.json"
R2SOURCE=ROOT/"status/national_R2_meteostat_station_source_evidence.json"
def sha(b):return hashlib.sha256(b).hexdigest()
j=json.loads(SUM.read_text(encoding="utf-8"))
r1=json.loads(R1SOURCE.read_text(encoding="utf-8"))
r2=json.loads(R2SOURCE.read_text(encoding="utf-8"))
if not(j["input_county_candidates"]==2847 and j["R1_longer_history_partial_counties"]==87
  and j["R2_longer_history_partial_counties"]==73
  and j["source_quality_intersection_counts"].get(
    "R1_LONGER_ERA5_OR_300MONTH_STATION_PARTIAL__R2_LONGER_ERA5_OR_300MONTH_STATION_PARTIAL")==73
  and j["formal_A_B_C_D_grades"]==0 and r1["R1_counties_with_any_real_point_including_short_history"]==214):
 raise RuntimeError("Frozen R1 R2 evidence quality source drift")
if sha(SOURCE.read_bytes())!=j["output_sha256"]["national_csv"]:
 raise RuntimeError("Joint national 2847 source SHA drift")
with SOURCE.open(encoding="utf-8-sig",newline="") as f:
 rd=csv.DictReader(f);rows=list(rd)
if len(rows)!=2847 or len({x["candidate_code"] for x in rows})!=2847:
 raise RuntimeError("Nonunique historical county candidate list")
selected=[r for r in rows if
 r["R1R2_temperature_evidence_tier"]=="LONGER_ERA5_OR_300MONTH_STATION_PARTIAL"
 and r["R1R2_rain_sun_evidence_tier"]=="LONGER_ERA5_OR_300MONTH_STATION_PARTIAL"]
if len(selected)!=73:raise RuntimeError("Longer history both parameters not 73: "+str(len(selected)))
# Master V1.2: winter 12-Feb daytime 18-25C, summer June-Sept daily max
# 25-29C, annual sun >=2200h, annual rain <=1000mm. These are *ideals*.
ideals={
 "winter_daytime_mean_max_c":{"lower":18,"upper":25,"source_standard":"MasterV1.2 §四, ideal not elimination"},
 "summer_jun_sep_daytime_max_c":{"lower":25,"upper":29,"source_standard":"MasterV1.2 §四, ideal not elimination"},
 "annual_sunshine_hours":{"lower":2200,"upper":None,"source_standard":"MasterV1.2 §四, ideal not elimination"},
 "annual_precipitation_mm":{"lower":None,"upper":1000,"source_standard":"MasterV1.2 §四, ideal not elimination"}}
def num(raw):
 if raw in (None,"","NAN","nan","None"):return None
 try:return float(raw)
 except (ValueError,TypeError):return None
def cmp(x,lo,hi):
 if x is None:return "NOT_MEASURED"
 if lo is not None and x<lo:return "BELOW_IDEAL_NOT_FATAL"
 if hi is not None and x>hi:return "ABOVE_IDEAL_NOT_FATAL"
 return "WITHIN_IDEAL_TARGET"
def choose(r,stationfield,era5field,source_station,source_era5):
 s=num(r.get(stationfield));e=num(r.get(era5field))
 if s is not None and e is not None:
  return s,source_station,"STATION_AND_ERA5_BOTH_EXIST_RETAINED_SEPARATELY",e
 if s is not None:return s,source_station,"ONE_SITE_SOURCE_ONLY",None
 if e is not None:return e,source_era5,"ONE_MODEL_GRID_SOURCE_ONLY",None
 return None,"NOT_AVAILABLE","NO_QA_PARAMETER_VALUE",None
metrickeys=list(ideals)
recs=[];counts={k:collections.Counter() for k in metrickeys}
st=collections.Counter();complete=0
for r in selected:
 code=r["candidate_code"];name=r["candidate_name"]
 station_r1=str(r.get("R1_meteostat_station_ids") or "")
 station_r2=str(r.get("R2_meteostat_station_id") or "")
 station_match=(station_r1!="" and station_r2!="" and station_r2 in station_r1.split(";"))
 w,wsrc,wcase,wera=choose(r,"R1_meteostat_winter_tmax_station_c","R1_winter_max_mean_c",
  "Meteostat_obs_station_monthly_TMAX_1991_2020_300PLUS_MONTHS","ERA5_OpenMeteo_1991_2020_POINT_GRID")
 su,susrc,sucase,suera=choose(r,"R1_meteostat_summer_tmax_station_c","R1_summer_jun_sep_max_mean_c",
  "Meteostat_obs_station_monthly_TMAX_1991_2020_300PLUS_MONTHS","ERA5_OpenMeteo_1991_2020_POINT_GRID")
 sun,sunsrc,suncase,sunera=choose(r,"R2_meteostat_annual_sunshine_hours","R2_annual_sunshine_hours",
  "Meteostat_obs_station_monthly_TSUN_1991_2020_300PLUS_MONTHS","ERA5_OpenMeteo_1991_2020_POINT_GRID")
 rain,rainsrc,raincase,rainera=choose(r,"R2_meteostat_precip_1991_2020_mm","R2_annual_rainfall_mm",
  "Meteostat_obs_station_monthly_PRCP_1991_2020_300PLUS_MONTHS","ERA5_OpenMeteo_1991_2020_POINT_GRID")
 vals=dict(zip(metrickeys,[w,su,sun,rain]))
 sources=dict(zip(metrickeys,[wsrc,susrc,sunsrc,rainsrc]))
 duplicates=dict(zip(metrickeys,[wera,suera,sunera,rainera]))
 mixed=not all(src.startswith("Meteostat") for src in sources.values() if src!="NOT_AVAILABLE")
 if station_r1 and station_r2 and not station_match:st["R1_R2_STATION_ID_MISMATCH"]+=1
 if any(v is not None for v in duplicates.values()):st["DUAL_METEO_ERA5_SOURCE_PRESENT"]+=1
 if mixed:st["AT_LEAST_ONE_ERA5_MODEL_GRID_METRIC"]+=1
 else:st["ONLY_METEOSTAT_VALUES_WHEN_MEASURED"]+=1
 statuses={k:cmp(vals[k],ideals[k]["lower"],ideals[k]["upper"]) for k in metrickeys}
 for k in metrickeys:counts[k][statuses[k]]+=1
 available=sum(v is not None for v in vals.values())
 inside=sum(z=="WITHIN_IDEAL_TARGET" for z in statuses.values())
 outside=sum("NOT_FATAL" in z for z in statuses.values())
 if available==4:complete+=1
 recs.append({"candidate_code":code,"county":name,"province_prefix":code[:2],
  "R1_source_station_id":station_r1,"R2_source_station_id":station_r2,
  "R1_R2_same_station_checked":station_match,
  "winter_12_2_daily_high_c":w,
  "summer_6_9_daily_high_c":su,
  "annual_sun_hours":sun,"annual_rain_mm":rain,
  "winter_ideal_status":statuses["winter_daytime_mean_max_c"],
  "summer_ideal_status":statuses["summer_jun_sep_daytime_max_c"],
  "sun_ideal_status":statuses["annual_sunshine_hours"],
  "rain_ideal_status":statuses["annual_precipitation_mm"],
  "winter_source":wsrc,"summer_source":susrc,
  "sun_source":sunsrc,"rain_source":rainsrc,
  "winter_alt_ERA5_point_c":wera,"summer_alt_ERA5_point_c":suera,
  "sun_alt_ERA5_point_h":sunera,"rain_alt_ERA5_point_mm":rainera,
  "sources_mixed_model_station":mixed,
  "metric_count_measured":available,"metric_count_within_ideal":inside,
  "metric_count_outside_ideal_not_fatal":outside,
  "missing_ideal_parameter_list":";".join(k for k,z in statuses.items() if z=="NOT_MEASURED"),
  "unmeasured_due_to_no_source":4-available,
  "next_missing_essential":"DAILY_EXTREME_35C_DAYS;ET_COMFORT_DAYS;MONTHLY_RAINY_STREAKS;LOCAL_HUMIDITY;RESIDENCE_ALTITUDE;PM25_O3;DRINKING_WATER;POLLUTED_LANDS;GEOHAZARD",
  "suitability_grade":"UNASSESSED_PENDING_RESIDENTIAL_AND_HEALTH_RISK",
  "early_elimination":False,
  "official_2026_county_confirmed":False,
  "time_series_1991_2020_full_360_months_verified":False,
  "scope_note":"longer_source_historic_county_climate_point_not_actual_residential_microclimate"})
# Emit source vs value and avoid rank being a formal A/B/C/D
cols=list(recs[0])
out=OUT/"national_73_longer_R1_R2_climate_ideal_preference_triage.csv"
with out.open("w",encoding="utf-8-sig",newline="") as f:
 wr=csv.DictWriter(f,fieldnames=cols);wr.writeheader();wr.writerows(recs)
summary={
 "schema":"RET_73_LONGER_HISTORY_COUNTY_CLIMATE_PREFERENCE_NOT_FATAL_TRIAGE_V1",
 "created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "frozen_master":"退休宜居城市_长期研究基线_Master_Latest.docx V1.2 §四, 五, 六, 七",
 "ideal_thresholds_not_hard_exclusions":ideals,
 "source_2847_joint_sha256":j["output_sha256"]["national_csv"],
 "input_2025_2026_provisional_2847":2847,
 "only_dual_longer_source_candidate_counties":73,
 "candidate_with_four_parameter_source_values":complete,
 "per_parameter_status_counts":{k:dict(z) for k,z in counts.items()},
 "source_quality_conflicts":dict(st),
 "candidates_with_all_four_within_ideal":sum(z["metric_count_within_ideal"]==4 for z in recs),
 "candidates_with_any_ideal_deviation":sum(z["metric_count_outside_ideal_not_fatal"]>=1 for z in recs),
 "candidates_with_two_or_more_ideal_deviations":sum(z["metric_count_outside_ideal_not_fatal"]>=2 for z in recs),
 "candidate_records":recs,
 "output_CSV_sha256":sha(out.read_bytes()),
 "official_2026_county_roster_or_residential_microclimate_verified":False,
 "no_formal_A_B_C_D_grades":0,
 "confirmed_county_eliminations":0,
 "nationwide_2847_candidate_register_unchanged":True,
 "limitations":["Preference thresholds are NOT medically hard elimination lines",
 "Longer-history station data 300+ observed months is not proof of complete 360-month official CMA normal",
 "Winter station daytime and ERA5 modeled point values must not be silently aggregated",
 "All 73 candidate residential geographic boundaries and elevation details remain pending",
 "Absence of daily heat extremes, ET, water pollution, ozone or geohazard prevents formal grade"]}
(OUT/"national_73_climate_ideal_source_comparison_evidence.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"candidates":len(recs),"all4available":complete,
 "byparam":summary["per_parameter_status_counts"],
 "fourwithin":summary["candidates_with_all_four_within_ideal"],
 "2plus_deviations":summary["candidates_with_two_or_more_ideal_deviations"],
 "source_conflicts":summary["source_quality_conflicts"]},ensure_ascii=False),flush=True)
