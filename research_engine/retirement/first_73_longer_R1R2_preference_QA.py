#!/usr/bin/env python3
"""First actual non-exclusion climate preference comparison for 73 county
candidates with longer-source R1 and R2 point evidence.

Formal Library V1.2 preference targets, NOT fatal climate thresholds:
winter Dec-Feb average daily MAX 18-25C, summer Jun-Sep mean daily MAX 25-29C,
annual sun >=2200 hours, annual precipitation <=1000mm.
Missing parameters are N/A, not negatives. Prioritize station observation
when present, archive independent ERA5 model value and disagreements;
no mixed-source average, no formal A/B/C/D or candidate elimination.
"""
import collections,csv,datetime,hashlib,json,pathlib
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT/"status/national_2847_R1_R2_joint_cascade_evidence_and_next_gap.csv"
SUM=ROOT/"status/national_2847_R1_R2_joint_cascade_summary.json"
def sha(b):return hashlib.sha256(b).hexdigest()
s=json.loads(SUM.read_text(encoding="utf-8"))
if s["R1_R2_both_partial_evidence"]!=199 or not any(
 x["count"]==73 and x["R1_tier"]=="LONGER_OR_ERA5_POINT_PARTIAL"
 and x["R2_tier"]=="LONGER_OR_ERA5_POINT_PARTIAL"
 for x in s["quality_tier_cross_counts"]):raise RuntimeError("Expected 73 longer source dual candidates absent")
if sha(SRC.read_bytes())!=s["national_cascade_csv_sha256"]:raise RuntimeError("Source 2847 national CSV hash drift")
with SRC.open(encoding="utf-8-sig",newline="") as f:
 reader=csv.DictReader(f);rows=list(reader)
if len(rows)!=2847:raise RuntimeError("Missing nationwide candidates")
strong=[x for x in rows if x["R1_evidence_quality_tier"]=="LONGER_OR_ERA5_POINT_PARTIAL" and x["R2_evidence_quality_tier"]=="LONGER_OR_ERA5_POINT_PARTIAL"]
if len(strong)!=73 or len({x["candidate_code"] for x in strong})!=73:raise RuntimeError("Strong 73 county cohort not unique")
def num(v):
 try:
  if v is None or str(v).strip()=="":return None
  return float(v)
 except Exception:raise RuntimeError("Bad numeric source value "+str(v))
def select(r,station_key,model_key,units):
 sv=num(r.get(station_key));mv=num(r.get(model_key))
 if sv is not None:return sv,"METEOSTAT_OBSERVATION_CLASS_STATION_300MONTH_CRITERION",mv
 if mv is not None:return mv,"ERA5_1991_2020_MODEL_GRID_POINT",None
 return None,"PARAMETER_NOT_AVAILABLE",None
def check(v,low,high):
 if v is None:return "MISSING_NOT_FAIL"
 if low is not None and v<low:return "BELOW_IDEAL_NON_FATAL"
 if high is not None and v>high:return "ABOVE_IDEAL_NON_FATAL"
 return "WITHIN_IDEAL_PREFERENCE_NOT_FORMAL_GRADE"
result=[];statuscounts=collections.defaultdict(collections.Counter);available=collections.Counter();sources=collections.Counter()
for r in strong:
 winter,ws,altw=select(r,"R1_meteostat_winter_tmax_station_c","R1_winter_max_mean_c","C")
 summer,ss,alts=select(r,"R1_meteostat_summer_tmax_station_c","R1_summer_jun_sep_max_mean_c","C")
 precip,ps,altp=select(r,"R2_meteostat_precip_1991_2020_mm","R2_annual_rainfall_mm","mm")
 sunshine,ls,altl=select(r,"R2_meteostat_annual_sunshine_hours","R2_annual_sunshine_hours","h")
 sources.update([ws,ss,ps,ls])
 tests={"winter_daytime_tmax":check(winter,18,25),
   "summer_daytime_tmax":check(summer,25,29),
   "annual_sunshine":check(sunshine,2200,None),
   "annual_precip":check(precip,None,1000)}
 for k,status in tests.items():
  statuscounts[k][status]+=1
  if status!="MISSING_NOT_FAIL":available[k]+=1
 mismatch=any(abs(a-b)>=3 for a,b in [(winter,altw),(summer,alts)] if a is not None and b is not None)
 record={"candidate_code":r["candidate_code"],"candidate_name":r["candidate_name"],
 "source_reference_winter_tmax_c":winter,"source_winter":ws,
 "source_reference_summer_tmax_c":summer,"source_summer":ss,
 "source_reference_precip_annual_mm":precip,"source_precip":ps,
 "source_reference_sunshine_annual_hours":sunshine,"source_sunshine":ls,
 "ERA5_independent_winter_tmax_if_both":altw,
 "ERA5_independent_summer_tmax_if_both":alts,
 "temperature_model_vs_station_difference_ge3C":mismatch,
 "winter_preference":tests["winter_daytime_tmax"],
 "summer_preference":tests["summer_daytime_tmax"],
 "sunshine_preference":tests["annual_sunshine"],
 "precip_preference":tests["annual_precip"],
 "measured_ideal_items":sum(z!="MISSING_NOT_FAIL" for z in tests.values()),
 "within_ideal_items_not_hard":sum(z=="WITHIN_IDEAL_PREFERENCE_NOT_FORMAL_GRADE" for z in tests.values()),
 "deviating_ideal_items_nonfatal":sum(z in ["BELOW_IDEAL_NON_FATAL","ABOVE_IDEAL_NON_FATAL"] for z in tests.values()),
 "missing_ideal_items":sum(z=="MISSING_NOT_FAIL" for z in tests.values()),
 "longer_data_quality":"ERA5_MODEL_OR_300MONTH_SOURCE_VETTED_STATION_NOT_FULL_360_MONTH_CERTIFIED_NORMAL",
 "full_R1_R2_climate_extremes_and_humidity_done":False,
 "air_water_pollution_residential_altitude_disaster_done":False,
 "2026_current_official_county_boundary_certified":False,
 "preference_screen_is_exclusion":False,
 "formal_A_B_C_D_grade":""}
 result.append(record)
if len(result)!=73 or sum(x["preference_screen_is_exclusion"] for x in result)!=0:raise RuntimeError("No exclusion authorized")
top_n_all4=sum(x["within_ideal_items_not_hard"]==4 and x["missing_ideal_items"]==0 for x in result)
p=OUT/"first_73_longer_source_climate_preference_nonfatal_audit.csv"
cols=list(result[0])
with p.open("w",encoding="utf-8-sig",newline="") as f:
 wr=csv.DictWriter(f,fieldnames=cols);wr.writeheader();wr.writerows(result)
out={"schema":"RET_FIRST_73_R1_R2_LONGER_SOURCE_CLIMATE_IDEALS_NONFATAL_AUDIT_V1",
 "asof_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "formal_baseline":"Library 退休宜居城市_长期研究基线_Master_Latest.docx V1.2, section 4, ideal non-hard values",
 "source_2847_national_csv_sha256":sha(SRC.read_bytes()),
 "source_2847_R1R2_summary_sha256":sha(SUM.read_bytes()),
 "analyzed_longer_source_R1R2_candidate_count":73,
 "winter_daytime_ideal_c_min":18,"winter_daytime_ideal_c_max":25,
 "summer_daytime_ideal_c_min":25,"summer_daytime_ideal_c_max":29,
 "annual_sunshine_ideal_min_hours":2200,
 "annual_rainfall_ideal_max_mm":1000,
 "ideal_type":"NON_HARD_USER_PREFERENCE_NOT_A_FATAL_HEALTH_THRESHOLD",
 "source_param_observation_count_by_type":dict(available),
 "parameter_status_counts":{k:dict(v) for k,v in statuscounts.items()},
 "source_type_counts":dict(sources),
 "all_four_ideal_preference_met_count":top_n_all4,
 "at_least_one_ideal_preference_met_count":sum(x["within_ideal_items_not_hard"]>=1 for x in result),
 "model_vs_station_3C_disagreement_cases":sum(x["temperature_model_vs_station_difference_ge3C"] for x in result),
 "county_audit_records":result,
 "output_73_csv_sha256":sha(p.read_bytes()),
 "previous_R1_any_partial_counties_unchanged":214,"previous_R2_any_partial_counties_unchanged":199,
 "national_carry_forward":2847,"formal_valid_county_screenings":0,"confirmed_county_exclusions":0,
 "limitations":["No A/B/C/D ranking or removal; user targets are ideal values, not hard pass-fail thresholds",
 "Winter/summer station source averages may cover 300/360 months; source does not assert full 1991-2020 CMA-certified normals",
 "ERA5 model and Meteostat station points may be different grid elevation/locations; both values preserved when both exist",
 "Annual sun, rainfall and temperature missingness does not mean poor environment",
 "Daily heat spells/ET, humidity, ozone/PM2.5, drinking water, pollution, disaster and residential altitude all require follow-up",
 "County code matches compiled 2025 history, latest 2026 official legal boundary still not verified"]}
(OUT/"first_73_longer_source_climate_preference_nonfatal_audit.json").write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({k:out[k] for k in ["analyzed_longer_source_R1R2_candidate_count",
 "source_param_observation_count_by_type","parameter_status_counts",
 "all_four_ideal_preference_met_count","at_least_one_ideal_preference_met_count",
 "model_vs_station_3C_disagreement_cases","formal_valid_county_screenings"]},ensure_ascii=False),flush=True)
