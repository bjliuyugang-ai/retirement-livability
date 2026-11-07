#!/usr/bin/env python3
"""R1/R2 NATIONAL JOINT EVIDENCE AUDIT over exact 2847 original county candidates.

Crosses true previous temperature evidence with independently sourced
precipitation/sunshine evidence. All provisional administrative 2026 codes
remain OPEN; tier <300 months is strictly an exploratory discovery layer.
No grading, no exclusions, and no climate cutoff silently manufactured.
"""
import collections,csv,datetime,hashlib,json,pathlib
ROOT=pathlib.Path("research_engine/retirement")
OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
SOURCE=ROOT/"status/national_R2_132_interim_obs_source_2847.csv"
R2=ROOT/"status/meteostat_CN132_interim_R2_evidence.json"
R1=ROOT/"status/meteostat_CN_226_R1_tiered_expansion_evidence.json"
OLD=ROOT/"status/national_R2_meteostat_station_source_evidence.json"
def digest(b):return hashlib.sha256(b).hexdigest()
a=json.loads(R1.read_text(encoding="utf-8"))
b=json.loads(R2.read_text(encoding="utf-8"))
old=json.loads(OLD.read_text(encoding="utf-8"))
if not (a["R1_counties_with_any_real_point_including_short_history"]==214
 and b["R1_all_partial_any_period_retained"]==214
 and b["R2_total_counties_any_partial_evidence_including_interim"]==199
 and b["prior_R2_longer_source_partials_retained"]==73
 and old["R2_total_partial_site_counties"]==73
 and b["formal_valid_county_screenings"]==0
 and b["confirmed_exclusions"]==0):
 raise RuntimeError("R1/R2 prerequisite quality tiers were altered")
if digest(SOURCE.read_bytes())!=b["national_output_csv_sha256"]:
 raise RuntimeError("Source R2 national CSV hash mismatch")
with SOURCE.open(encoding="utf-8-sig",newline="") as f:
 reader=csv.DictReader(f);fields=list(reader.fieldnames);rows=list(reader)
if len(rows)!=2847 or len({r["candidate_code"] for r in rows})!=2847:
 raise RuntimeError("Provisional county input 2847 not conserved")
if any(r["confirmed_exit_round"] for r in rows):
 raise RuntimeError("Fatal eliminations without authorized evidence")
if any(str(r.get("valid_county_screening","")).strip().lower()=="true" for r in rows):
 raise RuntimeError("Formal county screenings must not be silently added")
newcols=["R1R2_temperature_evidence_tier","R1R2_rain_sun_evidence_tier",
"R1R2_joint_evidence_quadrant","R1R2_distinct_observed_parameter_count",
"R1R2_rain_sufficiency_tier","R1R2_sun_sufficiency_tier",
"R1R2_time_window_warning","R1R2_next_data_gap_priority",
"R1R2_cross_parameter_ready_for_provisional_review","R1R2_provisional_grade",
"R1R2_2026_official_county_code_verified","R1R2_conclusion_and_exclusion"]
for name in newcols:
 if name in fields:raise RuntimeError("Joint audit would overwrite prior field "+name)
fields+=newcols
quads=collections.Counter();tiers=collections.Counter()
byprov=collections.defaultdict(lambda:collections.Counter())
first=[];stats={"rain_long":0,"rain_short":0,"sun_long":0,"sun_short":0,
 "rain_any":0,"sun_any":0,"temp_long":0,"temp_short":0,"both_long":0,"both_short":0,
 "long_temperature_short_R2":0,"short_temperature_long_R2":0,"both_partial":0,
 "rain_missing_with_R1":0,"sun_missing_with_R1":0}
for r in rows:
 code=r["candidate_code"];name=r["candidate_name"]
 R1s=r["R1_status"];R2s=r["R2_status"]
 if R1s=="NOT_SCREENED":t1="MISSING"
 elif R1s.startswith("INTERIM_"):t1="SHORT_HISTORY_180MONTH_DISCOVERY_ONLY"
 else:t1="LONGER_ERA5_OR_300MONTH_STATION_PARTIAL"
 if R2s=="NOT_SCREENED":t2="MISSING"
 elif R2s.startswith("INTERIM_"):t2="SHORT_HISTORY_180MONTH_DISCOVERY_ONLY"
 else:t2="LONGER_ERA5_OR_300MONTH_STATION_PARTIAL"
 has1=t1!="MISSING";has2=t2!="MISSING"
 q="BOTH_PARTIAL" if has1 and has2 else ("ONLY_R1_TEMPERATURE" if has1 else ("ONLY_R2_PRECIP_SUN" if has2 else "NEITHER_PARAMETER_EVIDENCE"))
 r["R1R2_temperature_evidence_tier"]=t1
 r["R1R2_rain_sun_evidence_tier"]=t2
 r["R1R2_joint_evidence_quadrant"]=q
 # Only values explicitly meeting the source-specific parameter gates count.
 rain_long=(r.get("R2_meteostat_precip_sufficiency")=="PASS" or r.get("R2_annual_rainfall_mm","")!="")
 sun_long=(r.get("R2_meteostat_sun_sufficiency")=="PASS" or r.get("R2_annual_sunshine_hours","")!="")
 rain_short=(r.get("R2_short_history_precip_source_status")=="OBS_180MO_MIN10YR_PER_CALENDAR_MONTH")
 sun_short=(r.get("R2_short_history_sunshine_source_status")=="OBS_180MO_MIN10YR_PER_CALENDAR_MONTH")
 rain="LONGER_PARTIAL" if rain_long else ("SHORT_HISTORY_DISCOVERY_ONLY" if rain_short else "NOT_SCANNED_OR_INSUFFICIENT")
 sun="LONGER_PARTIAL" if sun_long else ("SHORT_HISTORY_DISCOVERY_ONLY" if sun_short else "NOT_SCANNED_OR_INSUFFICIENT")
 r["R1R2_rain_sufficiency_tier"]=rain
 r["R1R2_sun_sufficiency_tier"]=sun
 param_count=int(has1)+int(rain!="NOT_SCANNED_OR_INSUFFICIENT")+int(sun!="NOT_SCANNED_OR_INSUFFICIENT")
 r["R1R2_distinct_observed_parameter_count"]=param_count
 bothlong=has1 and has2 and t1.startswith("LONGER") and t2.startswith("LONGER")
 if q=="BOTH_PARTIAL":
  if bothlong: r["R1R2_time_window_warning"]="LONGER_REFERENCE_POINT_DATA_NOT_CMA_OR_RESIDENTIAL_NORMAL"
  else:r["R1R2_time_window_warning"]="AT_LEAST_ONE_SHORT_HISTORY_SOURCE_NOT_VALID_30YEAR_NORMAL"
 else:r["R1R2_time_window_warning"]="MISSING_INDEPENDENT_TEMPERATURE_OR_RAIN_SUN_EVIDENCE"
 if not has1:nextgap="R1_TEMPERATURE_MODEL_OR_STATION_DATA"
 elif not has2:nextgap="R2_PRECIPITATION_SUNSHINE_STATION_OR_GRID_DATA"
 elif sun=="NOT_SCANNED_OR_INSUFFICIENT":nextgap="R2_SUNSHINE_MONTHLY_SOURCE_QA"
 elif rain=="NOT_SCANNED_OR_INSUFFICIENT":nextgap="R2_RAIN_MONTHLY_SOURCE_QA"
 elif not bothlong:nextgap="30YEAR_NORMALS_AND_STATION_COORDINATE_QA"
 else:nextgap="R3_ALTITUDE_R4_ENVIRONMENT_R5_WATER_AND_LOCAL_MICROCLIMATE"
 r["R1R2_next_data_gap_priority"]=nextgap
 r["R1R2_cross_parameter_ready_for_provisional_review"]="TRUE" if has1 and has2 else "FALSE"
 r["R1R2_provisional_grade"]=""
 r["R1R2_2026_official_county_code_verified"]="FALSE"
 r["R1R2_conclusion_and_exclusion"]="INDETERMINATE_KEEP_ACTIVE_NO_FORMAL_GRADE"
 quads[q]+=1;tiers[(t1,t2)]+=1
 byprov[code[:2]]["all"]+=1
 byprov[code[:2]][q]+=1
 for k,p in [("temp_long",t1.startswith("LONGER")),("temp_short",t1.startswith("SHORT")),
             ("rain_long",rain_long),("rain_short",rain_short and not rain_long),
             ("sun_long",sun_long),("sun_short",sun_short and not sun_long),
             ("rain_any",rain!="NOT_SCANNED_OR_INSUFFICIENT"),("sun_any",sun!="NOT_SCANNED_OR_INSUFFICIENT"),
             ("both_long",bothlong),("both_short",t1.startswith("SHORT") and t2.startswith("SHORT")),
             ("long_temperature_short_R2",t1.startswith("LONGER") and t2.startswith("SHORT")),
             ("short_temperature_long_R2",t1.startswith("SHORT") and t2.startswith("LONGER")),
             ("both_partial",has1 and has2),
             ("rain_missing_with_R1",has1 and rain=="NOT_SCANNED_OR_INSUFFICIENT"),
             ("sun_missing_with_R1",has1 and sun=="NOT_SCANNED_OR_INSUFFICIENT")]:
  stats[k]+=int(p)
 if q=="BOTH_PARTIAL":
  first.append({"candidate_code":code,"candidate_name":name,"temp_evidence_tier":t1,
   "rain_sun_evidence_tier":t2,"observed_parameter_count":param_count,
   "rain_tier":rain,"sun_tier":sun,
   "R1_winter_ERA5_daily_max_c":r.get("R1_winter_max_mean_c") or None,
   "R1_summer_ERA5_daily_max_c":r.get("R1_summer_jun_sep_max_mean_c") or None,
   "R1_Meteostat_station_winter_max_c":r.get("R1_meteostat_winter_tmax_station_c") or None,
   "R1_short_history_station_winter_max_c":r.get("R1_interim_15yr_winter_tmax_approx_station_c") or None,
   "R2_rain_longer_annual_mm":r.get("R2_meteostat_precip_1991_2020_mm") or None,
   "R2_rain_short_annual_mm":r.get("R2_short_history_precip_rough_annual_mm") or None,
   "R2_sun_longer_annual_hours":r.get("R2_meteostat_annual_sunshine_hours") or None,
   "R2_sun_short_annual_hours":r.get("R2_short_history_sunshine_rough_annual_hours") or None,
   "next_source_gap":nextgap,
   "climate_qualification":"NOT_ENOUGH_FOR_OFFICIAL_COUNTY_SCREENING"})
if quads["BOTH_PARTIAL"]+quads["ONLY_R1_TEMPERATURE"]+quads["ONLY_R2_PRECIP_SUN"]+quads["NEITHER_PARAMETER_EVIDENCE"]!=2847:
 raise RuntimeError("Quad evidence count not conserved")
R1n=quads["BOTH_PARTIAL"]+quads["ONLY_R1_TEMPERATURE"]
R2n=quads["BOTH_PARTIAL"]+quads["ONLY_R2_PRECIP_SUN"]
if R1n!=214 or R2n!=199:raise RuntimeError("Source evidence truth mismatch R1/R2 "+str((R1n,R2n)))
if stats["temp_long"]!=87 or stats["temp_short"]!=127:
 raise RuntimeError("Long vs short R1 definition changed "+str((stats["temp_long"],stats["temp_short"])))
if stats["both_partial"]!=quads["BOTH_PARTIAL"]:
 raise RuntimeError("Both partial field mismatch")
outcsv=OUT/"national_R1R2_joint_2847_evidence_and_missingness.csv"
with outcsv.open("w",encoding="utf-8-sig",newline="") as f:
 writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader();writer.writerows(rows)
priority=["LONGER_ERA5_OR_300MONTH_STATION_PARTIAL","SHORT_HISTORY_180MONTH_DISCOVERY_ONLY"]
first.sort(key=lambda z:(priority.index(z["temp_evidence_tier"]),
                      priority.index(z["rain_sun_evidence_tier"]),
                      -z["observed_parameter_count"],z["candidate_code"]))
dualcsv=OUT/"national_R1R2_both_evidence_first_candidate_review.csv"
with dualcsv.open("w",encoding="utf-8-sig",newline="") as f:
 writer=csv.DictWriter(f,fieldnames=list(first[0]) if first else ["candidate_code"]);writer.writeheader();writer.writerows(first)
provcsv=OUT/"national_R1R2_province_quality_coverage.csv"
pc=["province_prefix","total","both","only_R1","only_R2","neither"]
with provcsv.open("w",encoding="utf-8-sig",newline="") as f:
 writer=csv.DictWriter(f,fieldnames=pc);writer.writeheader()
 for prefix,counts in sorted(byprov.items()):
  writer.writerow({"province_prefix":prefix,"total":counts["all"],
   "both":counts["BOTH_PARTIAL"],"only_R1":counts["ONLY_R1_TEMPERATURE"],
   "only_R2":counts["ONLY_R2_PRECIP_SUN"],"neither":counts["NEITHER_PARAMETER_EVIDENCE"]})
report={"schema":"RET_NATIONAL_2847_R1_R2_EVIDENCE_CROSS_AND_TARGET_MISSINGNESS_V1",
 "created_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "exact_previous_R2_2847_csv_sha256":digest(SOURCE.read_bytes()),
 "exact_R1_226_evidence_json_sha256":digest(R1.read_bytes()),
 "exact_R2_132_evidence_json_sha256":digest(R2.read_bytes()),
 "input_county_candidates":2847,"R1_any_history_station_point_counties":R1n,
 "R1_longer_history_partial_counties":stats["temp_long"],
 "R1_short_history_observation_only_counties":stats["temp_short"],
 "R2_any_history_precip_or_sun_point_counties":R2n,
 "R2_longer_history_partial_counties":73,"R2_short_history_observation_only_counties":126,
 "four_quadrant_real_counts":dict(quads),
 "source_quality_intersection_counts":{"R1_"+k[0]+"__R2_"+k[1]:v for k,v in tiers.items()},
 "independent_parameter_source_counts":stats,
 "dual_evidence_counties_count":len(first),
 "dual_evidence_top_50_records":first[:50],
 "no_2026_official_county_denominator_certified":True,
 "formal_valid_county_screenings":0,"formal_A_B_C_D_grades":0,"confirmed_exclusions":0,
 "all_2847_carry_forward":2847,
 "next_action":"R3_TERRAIN_STATION_ELEVATION_COMPARISON_WITH_RESIDENTIAL_DEM_QA",
 "outputs":{"national_csv":"national_R1R2_joint_2847_evidence_and_missingness.csv",
 "dual_csv":"national_R1R2_both_evidence_first_candidate_review.csv",
 "province_csv":"national_R1R2_province_quality_coverage.csv"},
 "output_sha256":{"national_csv":digest(outcsv.read_bytes()),
 "dual_csv":digest(dualcsv.read_bytes()),"province_csv":digest(provcsv.read_bytes())},
 "limitations":["Evidence from one station can support more than one parameter; 'independent' refers to distinct parameter records, not independent physical measuring instruments",
 "R1-R2 dual evidence is NOT a pass/grade or evidence that local residence is suitable",
 "15-year discovery cohort must not be treated as climatological 1991-2020 official normal",
 "Full 2026 current official county boundaries and high resolution residential topography remain unverified",
 "No invented climate comfort threshold, county exit or source-proven hazardousness"]}
p=OUT/"national_R1R2_joint_missingness_evidence.json"
p.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"quadrants":report["four_quadrant_real_counts"],
 "R1_tiers":[stats["temp_long"],stats["temp_short"]],
 "R2_source_tiers":[73,126],
 "parameter_coverage":{k:stats[k] for k in ["rain_any","sun_any","rain_missing_with_R1","sun_missing_with_R1"]},
 "files":report["outputs"]},ensure_ascii=False),flush=True)
