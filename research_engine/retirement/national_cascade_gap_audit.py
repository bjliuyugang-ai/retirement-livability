#!/usr/bin/env python3
"""Honest audited snapshot of provisional 2847-county R0-R5 evidence cascade.

National round transitions are mechanically verified, but 100% valid nationwide
screening is NOT achieved. Distinguish NOT_SCANNED from measured-but-incomplete,
preserve the whole missing parameter tail, and never promote pilot point data
to formal administrative grade. No interaction with Library Master.
"""
import collections,csv,datetime,hashlib,json,pathlib
ROOT=pathlib.Path("research_engine/retirement");OUT=ROOT/"output";OUT.mkdir(parents=True,exist_ok=True)
R5CSV=ROOT/"status/national_r5_tap_water_batch.csv"
R5SUM=ROOT/"status/national_r5_tap_water_evidence.json"
R1SUM=ROOT/"status/national_r1_expanded_summary.json"
R2SUM=ROOT/"status/national_r2_first_real_batch_evidence.json"
R3SUM=ROOT/"status/national_r3_first_real_batch_evidence.json"
R4SUM=ROOT/"status/national_r4_city_context_evidence.json"
R0SUM=ROOT/"status/national_cascade_r0_summary.json"
def sha(b):return hashlib.sha256(b).hexdigest()
s0=json.loads(R0SUM.read_text(encoding="utf-8"))
s1=json.loads(R1SUM.read_text(encoding="utf-8"))
s2=json.loads(R2SUM.read_text(encoding="utf-8"))
s3=json.loads(R3SUM.read_text(encoding="utf-8"))
s4=json.loads(R4SUM.read_text(encoding="utf-8"))
s5=json.loads(R5SUM.read_text(encoding="utf-8"))
if s5["R5_carry_forward"]!=2847 or s4["R4_carry_forward"]!=2847 or s3["R3_carry_forward"]!=2847 or s2["R2_carry_forward"]!=2847 or s1["R1_carry_forward_to_R2"]!=2847:
 raise RuntimeError("Non-conserved national cascade")
if s0["candidate_count"]!=2847 or s0["2026_official_national_county_roster_verified"] is not False:
 raise RuntimeError("Invalid official-current disclaimer")
if sha(R5CSV.read_bytes())!=s5["CSV_sha256"]:raise RuntimeError("R5 source CSV hash mismatch")
with R5CSV.open(encoding="utf-8-sig",newline="") as f:
 dr=csv.DictReader(f);rs=list(dr)
if len(rs)!=2847 or len({x["candidate_code"] for x in rs})!=2847:
 raise RuntimeError("Missing or duplicate national county unit")
errors={x["code"]:x for x in s1["failure_details"]}
records=[];byprovince=collections.defaultdict(lambda:{"total":0,"R1_real":0,"R2_real":0,"R3_real":0,"R4_source":0,"R5_water":0,"none":0})
for r in rs:
 code=r["candidate_code"];name=r["candidate_name"];rounds={}
 for stage in range(1,6):
    k="R"+str(stage)
    raw=r[k+"_status"]
    scanned=raw!="NOT_SCREENED"
    rounds[k]={"status":raw,"has_actual_parameter_evidence":scanned,
      "current_county_validated":False,
      "spatial_limit":"NON_RESIDENTIAL_OR_MODEL_POINT" if scanned else "NO_SOURCE"}
 known=sum(x["has_actual_parameter_evidence"] for x in rounds.values())
 missing=[k for k,v in rounds.items() if not v["has_actual_parameter_evidence"]]
 incomplete=[k for k,v in rounds.items() if v["has_actual_parameter_evidence"]]
 if r["confirmed_exit_round"]:raise RuntimeError("Exclusion archive unexpectedly nonempty")
 if str(r["valid_county_screening"]).lower()=="true":raise RuntimeError("Formal county screening contamination")
 record={"geography_id":r["geography_id"],"county_code_candidate":code,"name":name,
 "province_prefix":code[:2],"administrative_source_class":r["source_class"],
 "official_2026_code_verified":False,
 "rounds":rounds,"parameter_rounds_with_partial_evidence":known,
 "not_scanned_parameters":missing,"scanned_but_incomplete_parameters":incomplete,
 "R1_winter_mean_daily_max_c":r.get("R1_winter_max_mean_c") or None,
 "R1_summer_jun_sep_mean_daily_max_c":r.get("R1_summer_jun_sep_max_mean_c") or None,
 "R1_hot_ge35_annual_days":r.get("R1_hot_ge35_days_per_year") or None,
 "R1_preference_signal":r.get("R1_preference_signal") or None,
 "R1_missing_note":r.get("R1_missing_parameters") or None,
 "R2_annual_sunshine_hours_model":r.get("R2_annual_sunshine_hours") or None,
 "R2_annual_rain_mm_model":r.get("R2_annual_rainfall_mm") or None,
 "R3_dem_sample_min_m":r.get("R3_DEM_sample_min_m") or None,
 "R3_dem_sample_max_m":r.get("R3_DEM_sample_max_m") or None,
 "R4_PM25_city_ug_m3":r.get("R4_city_annual_PM25_ug_m3") or None,
 "R4_city_good_air_days_pct":r.get("R4_city_good_air_day_rate_pct") or None,
 "R5_named_tap_sample_rows":r.get("R5_2026_Q1_Q3_official_tap_sample_rows") or None,
 "failed_R1_fetch_trace":errors.get(code),
 "queue_status":"PENDING_MISSING_OR_QUALITY_EVIDENCE",
 "first_confirmed_exit_round":None,"confirmed_exclusion":False,"reinstatement_condition":None,
 "formal_grade":None,"valid_county_screening":False,
 "candidate_suitability_not_inferred":True}
 records.append(record)
 agg=byprovince[code[:2]];agg["total"]+=1
 for j,k in enumerate(["R1_real","R2_real","R3_real","R4_source","R5_water"]):
    agg[k]+=int(rounds["R"+str(j+1)]["has_actual_parameter_evidence"])
 agg["none"]+=int(known==0)
known_counts=collections.Counter(x["parameter_rounds_with_partial_evidence"] for x in records)
if sorted(known_counts.items())!=[(0,2825),(1,10),(3,10),(4,1),(5,1)]:
 raise RuntimeError("Unexpected genuine evidence overlap: "+str(known_counts))
counts=[sum(z["rounds"][k]["has_actual_parameter_evidence"] for z in records) for k in ["R1","R2","R3","R4","R5"]]
if counts!=[22,12,12,2,1]:raise RuntimeError("Round observed coverage changed: "+str(counts))
failpop=len(errors)
if failpop!=20:raise RuntimeError("Rate-limit failure record discrepancy")
outputcsv=OUT/"national_cascade_all_2847_audit.csv"
columns=["county_code_candidate","name","province_prefix","administrative_source_class","official_2026_code_verified",
 "R1_status","R2_status","R3_status","R4_status","R5_status","parameter_rounds_with_partial_evidence",
 "not_scanned_parameters","scanned_but_incomplete_parameters",
 "R1_winter_mean_daily_max_c","R1_summer_jun_sep_mean_daily_max_c","R1_hot_ge35_annual_days",
 "R1_preference_signal","R2_annual_sunshine_hours_model","R2_annual_rain_mm_model",
 "R3_dem_sample_min_m","R3_dem_sample_max_m","R4_PM25_city_ug_m3","R4_city_good_air_days_pct",
 "R5_named_tap_sample_rows","failed_R1_fetch_trace","queue_status","first_confirmed_exit_round",
 "confirmed_exclusion","formal_grade","valid_county_screening"]
with outputcsv.open("w",encoding="utf-8-sig",newline="") as f:
 w=csv.DictWriter(f,fieldnames=columns);w.writeheader()
 for x in records:
  d={k:x.get(k) for k in columns}
  for stage in ["R1","R2","R3","R4","R5"]:d[stage+"_status"]=x["rounds"][stage]["status"]
  for k in ["not_scanned_parameters","scanned_but_incomplete_parameters"]:
   d[k]="; ".join(x[k])
  d["failed_R1_fetch_trace"]=json.dumps(x["failed_R1_fetch_trace"],ensure_ascii=False) if x["failed_R1_fetch_trace"] else ""
  w.writerow(d)
province_file=OUT/"national_cascade_province_coverage.csv"
with province_file.open("w",encoding="utf-8-sig",newline="") as f:
 w=csv.DictWriter(f,fieldnames=["province_prefix","total","R1_real","R2_real","R3_real","R4_source","R5_water","none"])
 w.writeheader()
 for code in sorted(byprovince):w.writerow({"province_prefix":code,**byprovince[code]})
result={"schema":"RET_NATIONAL_2847_COUNTY_PARAM_CASCADE_MISSING_AND_COVERAGE_AUDIT_V1",
"generated_at_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"scope":"Provisional nonofficial 2026-06 county candidate roster, 2017-2025 exploratory links",
"provisional_input_counties":2847,
"official_current_2026_county_roster_certified":False,
"provisional_counties_with_some_real_parameter_evidence":sum(known>0 for known in known_counts.elements()),
"provisional_counties_with_zero_parameter_evidence":known_counts[0],
"evidence_overlap_by_round_count":dict(sorted(known_counts.items())),
"R1_with_real_point_temperature":counts[0],"R1_not_scanned":2847-counts[0],
"R2_with_point_sun_rain":counts[1],"R2_not_scanned":2847-counts[1],
"R3_with_three_point_DEM":counts[2],"R3_not_scanned":2847-counts[2],
"R4_with_city_or_regional_air_context":counts[3],"R4_not_scanned":2847-counts[3],
"R5_with_named_tap_observations_counties":counts[4],"R5_not_scanned":2847-counts[4],
"R1_api_failed_candidate_count":failpop,
"confirmed_exclusions":0,"cumulative_R1_to_R5_carry_forward":2847,
"formal_valid_county_screenings":0,"formal_grades_modified":0,
"geographic_coverage_unit":"County code candidates, not actual dwelling polygons",
"R1_actual_data_coverage_fraction":round(counts[0]/2847,5),
"R2_actual_data_coverage_fraction":round(counts[1]/2847,5),
"R3_actual_data_coverage_fraction":round(counts[2]/2847,5),
"R4_actual_data_coverage_fraction":round(counts[3]/2847,5),
"R5_actual_data_coverage_fraction":round(counts[4]/2847,5),
"source_status_paths":{
 "R0":"research_engine/retirement/status/national_cascade_r0_summary.json",
 "R1":"research_engine/retirement/status/national_r1_expanded_summary.json",
 "R2":"research_engine/retirement/status/national_r2_first_real_batch_evidence.json",
 "R3":"research_engine/retirement/status/national_r3_first_real_batch_evidence.json",
 "R4":"research_engine/retirement/status/national_r4_city_context_evidence.json",
 "R5":"research_engine/retirement/status/national_r5_tap_water_evidence.json"},
"source_sha256":{str(p):sha(p.read_bytes()) for p in [R0SUM,R1SUM,R2SUM,R3SUM,R4SUM,R5SUM]},
"output_all_counties_csv_sha256":sha(outputcsv.read_bytes()),
"output_by_province_csv_sha256":sha(province_file.read_bytes()),
"top_evidence_counties":[{"code":x["county_code_candidate"],"name":x["name"],
 "partial_parameter_rounds":x["parameter_rounds_with_partial_evidence"],
 "missing":x["not_scanned_parameters"]} for x in sorted(records,key=lambda z:(-z["parameter_rounds_with_partial_evidence"],z["county_code_candidate"]))[:22]],
"R1_failed_sources":s1["failure_details"],
"decision":"THIS_IS_AN_INTERIM_MISSING_DATA_AUDIT; THE FIVE ROUNDS HAVE TECHNICALLY EXECUTED BUT NATIONWIDE VALID_SCREENING IS FAR_FROM_COMPLETE",
"hard_limits":["No formal nationwide denominator from current official 2026 record",
 "No 2026 legal identity certification for provisional 2847",
 "Climatology of model point is not county-wide validated nor station normal",
 "Citywide air data is not residential PM2.5/O3 evidence",
 "Sixteen 2026 named tap samples are not full municipal or residential potability evidence",
 "No confirmed residential hazard assessment for all provinces",
 "Unknowns are not to be excluded; no certified unmitigable fatal case was established"]}
jsonpath=OUT/"national_cascade_gap_coverage_audit.json"
jsonpath.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
print(json.dumps({"input":2847,"any_parameter_data":2847-known_counts[0],
"none":known_counts[0],"round_actual_coverage":counts,
"R1_api_blocked":failpop,"excluded":0,"formal_valid":0},ensure_ascii=False),flush=True)
